# Metro Böceği

Ana karakteri bir hamam böceği olan, Subway Surfers tarzı 3D sonsuz koşu oyunu. **iOS, Android** ve web tarayıcısında çalışır.

- Metro tünelinde üç şeritte koş, ekmek kırıntılarını topla.
- Trenlerden kaç, bariyerlerin ve böcek ilacı kutularının üstünden zıpla, tel çitlerin altından yassılarak geç.
- Kanat güçlendiricisi seni 7 saniye uçurur.
- Bir kez tökezlersen terlik peşine düşer; ikinci tökezlemede ezilirsin.

## Kontroller

| Telefon | Klavye | Hareket |
| --- | --- | --- |
| Sola / sağa kaydır | ← / → | Şerit değiştir |
| Yukarı kaydır | ↑ / Boşluk | Zıpla |
| Aşağı kaydır | ↓ | Yassıl / kay |
| ⏸ düğmesi | P / Esc | Duraklat |

## Proje yapısı

```
www/                 Oyunun kendisi (HTML + Three.js, internetsiz çalışır)
  index.html         Oyun kodu
  vendor/three/      Three.js r160 (yerel kopya)
  fonts/             Yazı tipleri (yerel kopya)
  manifest.webmanifest, sw.js   Ana ekrana eklenebilir web uygulaması (PWA)
android/             Android uygulaması (Capacitor)
ios/                 iOS uygulaması (Capacitor, Xcode projesi)
resources/           Uygulama simgesi ve açılış ekranı kaynakları
```

Oyun dikey ekran için ayarlıdır. Telefonda kamera üç şeridi de gösterecek şekilde geri çekilir, yavaş cihazlarda çözünürlük, ışık parlaması ve gölgeler otomatik olarak kısılır.

## Android

**Hazır APK:** Her `git push` sonrası GitHub Actions'taki **Android APK** iş akışı `app-debug.apk` üretir. Repo sayfasında *Actions → Android APK → son çalışma → Artifacts* altından indir, telefona at ve kur (ayarlardan "bilinmeyen kaynaklardan yükleme" izni gerekir).

**Kendin derlemek için** (Android Studio + JDK 17):

```
npm install
npx cap sync android
cd android && ./gradlew assembleDebug      # veya: npm run android (Android Studio'da açar)
```

Google Play'e yüklemek için Android Studio'da *Build → Generate Signed Bundle (AAB)* kullan.

## iOS

iOS uygulaması derlemek için **Mac + Xcode** gerekir (Apple kuralı).

```
npm install
npx cap sync ios
npm run ios          # Xcode'da açar
```

Xcode'da *Signing & Capabilities* bölümünden Apple hesabını (ücretsiz hesap kendi iPhone'una kurmak için yeterli) seç, iPhone'u bağla ve ▶ ile çalıştır. App Store için ücretli Apple Developer hesabı gerekir.

GitHub Actions'taki **iOS build check** iş akışı her push'ta projenin iOS simülatörü için derlendiğini doğrular.

**Mac olmadan iPhone'da oynamak:** `www/` klasörünü HTTPS üzerinden yayınla (ör. GitHub Pages), iPhone'da Safari ile aç, *Paylaş → Ana Ekrana Ekle*. Oyun tam ekran, simgesiyle ve internetsiz çalışır. Android'de Chrome'da *Uygulamayı yükle* aynı işi yapar.

## Web'de çalıştırma

```
npm run serve        # http://localhost:8080
```

`file://` ile doğrudan açmak çalışmaz (tarayıcılar modül dosyalarını engeller); yerel bir sunucu kullan.

## Notlar

- iPhone'da sessiz mod düğmesi açıksa oyun sesi duyulmaz.
- Simge ve açılış ekranı değişirse: `resources/icon.png` ve `resources/splash.png` dosyalarını güncelle, `npm run assets` çalıştır.
- Tüm dokular (beton, metro karoları, balast, traversler, tren, böcek kabuğu) kod içinde üretilir.
