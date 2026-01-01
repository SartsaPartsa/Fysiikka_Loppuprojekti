# Fysiikka_Loppuprojekti

Soveltava matematiikka ja fysiikka ohjelmoinnissa kurssin fysiikan osuuden loppuprojekti - Sara Vehviläinen

## 📋 Kuvaus

Matkapuhelimen sensoreilla mitatun kiihtyvyys- ja GPS-datan analyysi Streamlit-sovelluksella.

Tämä sovellus analysoi Phyphox-sovelluksella kerättyä dataa ja laskee:
- Askelmäärän kahdella eri menetelmällä (aikataso ja Fourier-analyysi)
- Kuljetun matkan GPS-datan perusteella
- Keskinopeuden
- Askelpituuden

Sovellus visualisoi myös:
- Suodatetun kiihtyvyysdatan (havaitut askeleet merkitty punaisina pisteinä)
- Tehospektritiheyden (PSD) kävelytaajuusalueella
- Kuljetun reitin interaktiivisella kartalla (Folium)
  - Reitti näkyy punaisena viivana
  - Aloitus- ja lopetuspisteet merkitty

## 🚀 Käyttöönotto

### 1. Asenna riippuvuudet

```bash
pip install -r requirements.txt
```

### 2. Käynnistä sovellus

```bash
streamlit run app.py
```

### 3. Lataa datatiedostot

Lataa Phyphoxista saadut CSV-tiedostot sivupalkin kautta:
- `Linear Accelerometer.csv` - kiihtyvyysdata
- `Location.csv` - GPS-data

**Huom!** Esimerkkidatatiedostot löytyvät `Fysiikka_mittaukset/`-kansiosta tässä repositoriossa. Voit käyttää myös omia Phyphox-sovelluksella kerättyjä mittauksia.

Sovellus käyttää file uploader -toimintoa, joten voit ladata tiedostot suoraan selaimessa ilman että ne tarvitsee tallentaa projektin hakemistoon.

### 4. Käytä sovellusta

1. Valitse kiihtyvyysakseli (X, Y tai Z) - yleensä Z-akseli näyttää kävelyn parhaiten
2. Halutessasi rajaa analysoitava aikaväli liukusäätimellä (esim. poista alku, jolloin et liikkunut)
3. Tarkastele tuloksia ja kuvaajia

## 📊 Ominaisuudet

### Käyttöliittymä
- **File uploader**: Lataa CSV-tiedostot suoraan selaimessa
- **Akselin valinta**: Valitse X, Y tai Z-akseli kiihtyvyysanalyysiä varten
- **Aikavälin rajaus**: Rajaa analysoitava aikajakso liukusäätimellä
- **Automaattiset asetukset**: Suodatus ja kynnysarvot optimoitu kävelylle

### Laskettavat arvot
- Askelmäärä aikatasossa (huippujen etsintä)
- Askelmäärä Fourier-analyysillä
- Kuljettu matka (GPS)
- Keskinopeus (m/s ja km/h)
- Askelpituus

### Visualisoinnit
- Suodatettu kiihtyvyysdata + havaitut askeleet
- Tehospektritiheys (PSD) kävelytaajuusalueella
- Interaktiivinen kartta (Folium) punaisella reittiviivalla

## 📊 Mittausohjeet

1. Avaa Phyphox-sovellus
2. Valitse `+` (Add simple experiment)
3. Valitse sensorit:
   - Linear Acceleration
   - Location
4. Käynnistä mittaus ja kävele vähintään muutama minuutti
   - Aloita hitaasti, sitten nopeammin, lopuksi juokse
5. Vie data CSV-muodossa
6. Lataa tiedostot tähän sovellukseen

## 📁 Tiedostorakenne

```
Fysiikka_Loppuprojekti/
├── app.py                    # Streamlit-sovellus
├── requirements.txt          # Python-riippuvuudet
├── README.md                # Tämä tiedosto
└── Fysiikka_mittaukset/     # Mittausdata-kansio
    ├── Linear Accelerometer.csv  # Kiihtyvyysdata
    ├── Location.csv              # GPS-data
    └── meta/                     # Metatiedot
        ├── device.csv
        └── time.csv
```

## 🔬 Menetelmät

### Askelmäärän laskenta aikatasossa
- Bandpass-suodatus (0.5-5 Hz) - kiinteät arvot optimoitu kävelylle
- Huippujen (peaks) etsintä suodatetusta signaalista
- Kynnyskerroin 0.3 × RMS (kiinteä arvo)
- Minimiväli huippujen välillä estää vääriä havaintoja

### Askelmäärän laskenta Fourier-analyysillä
- Welch-menetelmä tehospektritiheyden laskentaan
- Dominoivan taajuuden etsintä kävelytaajuusalueelta (0.5-4 Hz)
- Askelmäärä = taajuus × mittausaika

### GPS-analyysi
- Haversine-kaava etäisyyden laskentaan GPS-pisteiden välillä
- Kokonaismatka = pisteiden välisten etäisyyksien summa
- Keskinopeus = kokonaismatka / aika
- Interaktiivinen kartta Folium-kirjastolla
- Askelpituus = matka / askelmäärä

## 📝 Huomiot

- Sovellus käyttää file uploader -toimintoa - ei tarvitse hardcodata tiedostopolkuja
- **Akselin valinta**: Yleensä Z-akseli näyttää pystysuuntaisen liikkeen parhaiten
- **Aikavälin rajaus**: Voit poistaa mittauksen alun/lopun, jolloin et liikkunut
- **Kiinteät asetukset**: Suodatus (0.5-5 Hz) ja kynnysarvot optimoitu kävelylle
- GPS-sarakkeet: "Latitude (°)" ja "Longitude (°)"
- Kiihtyvyyssarakkeet: "Time (s)", "X (m/s^2)", "Y (m/s^2)", "Z (m/s^2)"
- GPS-signaalin löytyminen voi kestää hetken mittauksen alussa
- Pidä puhelin samassa asennossa koko mittauksen ajan
- Sovellus toimii sekä paikallisesti että voidaan julkaista Streamlit Cloudissa
