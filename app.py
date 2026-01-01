# Liikemittauksen analyysi - Fysiikan loppuprojekti
# Analysoi Phyphox-data: kiihtyvyys + GPS → askeleet, matka, nopeus

import streamlit as st
import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt, welch, find_peaks
from math import radians, sin, cos, asin, sqrt
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

# Poistaa kiihtyvyysdatasta kohinan, jättää vain kävelyn aiheuttamat heilahdukset
def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = max(lowcut / nyq, 1e-4)
    high = min(highcut / nyq, 0.99)
    if low >= high:
        low = 0.1
        high = 0.9
    b, a = butter(order, [low, high], btype="band")
    return b, a


def apply_filter(signal, fs, lowcut=0.5, highcut=5.0):
    b, a = butter_bandpass(lowcut, highcut, fs)
    return filtfilt(b, a, signal)


# Laskee askeleet etsimällä kiihtyvyyskäyrän huiput (kun jalka osuu maahan)
def detect_steps_time_domain(acc, fs, threshold_factor=0.3):
    acc = np.asarray(acc)
    if len(acc) == 0:
        return np.array([], dtype=int)

    min_distance = int(fs / 4.0) if fs > 0 else 1  # Askelten väli (max 4 askelta/sekunti)
    rms = np.sqrt(np.mean(acc**2))
    threshold = threshold_factor * rms

    peaks, _ = find_peaks(acc, height=threshold, distance=min_distance)
    return peaks


# Laskee askeleet analysoimalla, kuinka monta kertaa sekunnissa jalka osuu maahan
def estimate_steps_fourier(acc, t):
    acc = np.asarray(acc)
    t = np.asarray(t)

    if len(acc) < 4 or len(t) < 4:
        return 0, np.array([]), np.array([]), None

    fs = 1.0 / np.mean(np.diff(t))
    freqs, psd = welch(acc, fs=fs, nperseg=min(256, len(acc)))

    # Rajataan normaali kävelynopeus (0.5–4 askelta sekunnissa)
    mask = (freqs >= 0.5) & (freqs <= 4.0)
    freqs_roi = freqs[mask]
    psd_roi = psd[mask]

    if len(freqs_roi) == 0:
        return 0, freqs_roi, psd_roi, None

    peak_idx = np.argmax(psd_roi)
    f_peak = freqs_roi[peak_idx]
    duration = t[-1] - t[0]
    step_count = int(round(f_peak * duration)) if duration > 0 else 0

    return step_count, freqs_roi, psd_roi, f_peak


# Laskee kahden GPS-pisteen välisen etäisyyden maan pintaa pitkin
def haversine(lat1, lon1, lat2, lon2):
    R = 6371e3
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)

    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


# Laskee GPS-datasta kuljetun matkan ja keskinopeuden
def gps_distance_and_speed(df_loc):
    df = df_loc.dropna(subset=["Latitude (°)", "Longitude (°)"]).copy()

    if len(df) < 2:
        return 0.0, 0.0

    dists = []
    for i in range(1, len(df)):
        d = haversine(
            df["Latitude (°)"].iloc[i - 1],
            df["Longitude (°)"].iloc[i - 1],
            df["Latitude (°)"].iloc[i],
            df["Longitude (°)"].iloc[i],
        )
        dists.append(d)

    total_distance = np.sum(dists)
    duration = df["Time (s)"].iloc[-1] - df["Time (s)"].iloc[0]
    avg_speed = total_distance / duration if duration > 0 else 0.0

    return total_distance, avg_speed


# Valitsee kiihtyvyysakselin (X/Y/Z), joka näyttää kävelyn selkeimmin
def choose_best_axis(ax, ay, az, fs):
    axes = {
        "X": ax.values,
        "Y": ay.values,
        "Z": az.values,
    }

    best_axis = "Z"
    best_peak_power = -np.inf

    for name, sig in axes.items():
        acc = np.asarray(sig)
        if len(acc) < 4:
            continue

        freqs, psd = welch(acc, fs=fs, nperseg=min(256, len(acc)))
        mask = (freqs >= 0.5) & (freqs <= 4.0)
        if not np.any(mask):
            continue

        peak_power = psd[mask].max()
        if peak_power > best_peak_power:
            best_peak_power = peak_power
            best_axis = name

    return best_axis, axes[best_axis]


# STREAMLIT-SOVELLUS

st.title("Liikemittauksen analyysi (kiihtyvyys + GPS)")
st.write("Fysiikan loppuprojekti - Matkapuhelimen sensoridatan analyysi")

# Latauspainikkeet
st.sidebar.header("Lataa CSV-tiedostot")
acc_file = st.sidebar.file_uploader("Accelerometer.csv", type=["csv"])
loc_file = st.sidebar.file_uploader("Location.csv", type=["csv"])

if acc_file and loc_file:

    acc_df = pd.read_csv(acc_file)
    loc_df = pd.read_csv(loc_file)

    st.subheader("Raakadatan esikatselu")
    with st.expander("Näytä raakadata"):
        st.write("**Kiihtyvyysdata:**")
        st.write(acc_df.head())
        st.write("**GPS-data:**")
        st.write(loc_df.head())

    # Luetaan aika ja kiihtyvyysakselelit (X, Y, Z)
    time_all = acc_df.iloc[:, 0].astype(float)
    ax_all = acc_df.iloc[:, 1]
    ay_all = acc_df.iloc[:, 2]
    az_all = acc_df.iloc[:, 3]

    st.sidebar.subheader("Rajaa analysoitava aika")
    t_min = float(time_all.min())
    t_max = float(time_all.max())
    start_time, end_time = st.sidebar.slider(
        "Aikaväli kiihtyvyysdatasta (s)",
        min_value=t_min,
        max_value=t_max,
        value=(t_min, t_max),
    )

    mask_acc = (time_all >= start_time) & (time_all <= end_time)
    time_acc = time_all[mask_acc]
    ax = ax_all[mask_acc]
    ay = ay_all[mask_acc]
    az = az_all[mask_acc]

    if len(time_acc) < 4:
        st.error("Valitulla aikavälillä ei ole riittävästi kiihtyvyysdataa analyysiin.")
    else:
        st.sidebar.subheader("Valitse kiihtyvyysakseli")
        st.sidebar.caption("💡 Vinkki: Z-akseli näyttää yleensä kävelyn parhaiten")
        axis_choice = st.sidebar.radio("Akseli", ["X", "Y", "Z"], index=2)

        if axis_choice == "X":
            acc_raw = ax.values
        elif axis_choice == "Y":
            acc_raw = ay.values
        else:
            acc_raw = az.values

        fs = 1.0 / np.mean(np.diff(time_acc.values))
        lowcut = 0.5
        highcut = min(5.0, 0.45 * fs)
        acc_filt = apply_filter(acc_raw, fs, lowcut=lowcut, highcut=highcut)

        peaks = detect_steps_time_domain(acc_filt, fs, threshold_factor=0.3)
        step_count_time = len(peaks)

        step_count_fft, freqs_roi, psd_roi, f_peak = estimate_steps_fourier(
            acc_filt, time_acc
        )
        if "Time (s)" in loc_df.columns:
            time_loc_all = loc_df["Time (s)"].astype(float)
            mask_loc = (time_loc_all >= start_time) & (time_loc_all <= end_time)
            loc_df_segment = loc_df[mask_loc].copy()
        else:
            loc_df_segment = loc_df.copy()

        total_distance, avg_speed = gps_distance_and_speed(loc_df_segment)
        step_length = total_distance / step_count_time if step_count_time > 0 else 0.0

        # TULOKSET
        st.subheader("📊 Tulokset")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Askelmäärä (aikataso)", step_count_time)
            st.metric("Askelmäärä (Fourier)", step_count_fft)

        with col2:
            st.metric("Matka", f"{total_distance:.1f} m")
            st.metric("Matka (km)", f"{total_distance/1000:.3f} km")

        with col3:
            st.metric("Keskinopeus", f"{avg_speed:.2f} m/s")
            st.metric("Keskinopeus (km/h)", f"{avg_speed*3.6:.2f} km/h")

        st.metric("Askelpituus", f"{step_length:.2f} m")

        st.subheader("📈 Suodatettu kiihtyvyys ja havaitut askeleet")

        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(time_acc, acc_filt, label="Suodatettu kiihtyvyys", linewidth=1)
        if len(peaks) > 0:
            ax1.plot(
                time_acc.iloc[peaks],
                acc_filt[peaks],
                "o",
                label="Havaitut askeleet",
                markersize=5,
            )
        ax1.set_xlabel("Aika (s)")
        ax1.set_ylabel("Kiihtyvyys (m/s²)")
        ax1.set_title(f"Suodatettu kiihtyvyys ({axis_choice}-akseli)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        st.pyplot(fig1)

        st.subheader("📉 Tehospektritiheys (PSD)")

        fig2, ax2 = plt.subplots(figsize=(10, 4))
        if len(freqs_roi) > 0:
            ax2.semilogy(freqs_roi, psd_roi, linewidth=2)
            if f_peak is not None:
                ax2.axvline(f_peak, linestyle="--", alpha=0.7)
                ax2.text(
                    f_peak,
                    psd_roi.max(),
                    f"{f_peak:.2f} Hz",
                    ha="center",
                    va="bottom",
                )
        ax2.set_xlabel("Taajuus (Hz)")
        ax2.set_ylabel("Teho (log-asteikko)")
        ax2.set_title(f"Tehospektritiheys (kävelytaajuusalue 0.5–4 Hz, {axis_choice}-akseli)")
        ax2.grid(True, alpha=0.3)
        st.pyplot(fig2)

        st.subheader("🗺️ Reitti kartalla")

        if "Latitude (°)" in loc_df_segment.columns and "Longitude (°)" in loc_df_segment.columns:
            gps_df = loc_df_segment[["Latitude (°)", "Longitude (°)"]].dropna()
        else:
            gps_df = loc_df[["Latitude (°)", "Longitude (°)"]].dropna()

        if len(gps_df) > 0:
            center_lat = gps_df["Latitude (°)"].mean()
            center_lon = gps_df["Longitude (°)"].mean()
            m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
            route_coords = list(zip(gps_df["Latitude (°)"], gps_df["Longitude (°)"]))

            folium.PolyLine(
                route_coords,
                weight=4,
                opacity=0.8,
            ).add_to(m)

            folium.Marker(
                route_coords[0],
                popup="Aloitus",
                icon=folium.Icon(color="green", icon="play"),
            ).add_to(m)

            folium.Marker(
                route_coords[-1],
                popup="Lopetus",
                icon=folium.Icon(color="red", icon="stop"),
            ).add_to(m)

            st_folium(m, width=700, height=500)
        else:
            st.warning("Valitulla aikavälillä GPS-datassa ei ole kelvollisia sijaintipisteitä.")

else:
    st.info("📁 Lataa molemmat tiedostot (Accelerometer.csv ja Location.csv) sivupalkista aloittaaksesi analyysin.")
    st.write(
        """
        ### Ohjeet:
        1. Lataa Phyphoxista saadut CSV-tiedostot vasemman sivupalkin kautta
        2. Valitse kiihtyvyysakseli (yleensä Z)
        3. Halutessasi rajaa pois alku, jolloin et liikkunut
        4. Tarkastele tuloksia ja kuvaajia

        ### Tiedot:
        - **Accelerometer.csv**: Sisältää kiihtyvyysdatan (X, Y, Z -akselit)
        - **Location.csv**: Sisältää GPS-datan (leveyspiiri, pituuspiiri, aika)
        """
    )