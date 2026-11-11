# Metro Böceği

Ana karakteri bir hamam böceği olan, Subway Surfers tarzı sonsuz koşu oyunu. Tarayıcıda çalışır (Three.js, WebGL).

- Metro tünelinde üç şeritte koş, ekmek kırıntılarını topla.
- Trenlerden kaç, bariyerlerin ve böcek ilacı kutularının üstünden zıpla, tel çitlerin altından yassılarak geç.
- Kanat güçlendiricisi seni 7 saniye uçurur.
- Bir kez tökezlersen terlik peşine düşer; ikinci tökezlemede ezilirsin.

## Oynamak

`index.html` dosyasını bir tarayıcıda aç (internet bağlantısı gerekir, Three.js CDN'den yüklenir) veya yerel bir sunucu ile çalıştır:

```
python3 -m http.server 8000
```

## Kontroller

| Tuş | Hareket |
| --- | --- |
| ← / → (A / D) | Şerit değiştir |
| ↑ / Boşluk (W) | Zıpla |
| ↓ (S) | Yassıl / kay |
| P / Esc | Duraklat |
| Telefon | Kaydırma hareketleri |

Tüm dokular (beton, metro karoları, balast, ahşap traversler, tren gövdesi, böcek kabuğu) kod içinde prosedürel olarak üretilir; harici görsel dosyası yoktur.
