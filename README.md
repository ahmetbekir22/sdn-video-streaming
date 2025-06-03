İşte istediğin şekilde kapsamlı ve iki bölüme ayrılmış bir `.md` (Markdown) proje dökümanı:
**1. bölümde ne yapman gerektiği**,
**2. bölümde nasıl yapacağın, hangi araçları/dilleri kullanacağın ve nelere dikkat edeceğin** açıkça belirtilmiştir.

---

```markdown
# SDN Final Project: Video Streaming with Load Balancing (Mininet + Python)

## 📘 Bölüm 1 – Projede Yapılacaklar (Ne Yapmalıyım?)

Bu bölüm, proje boyunca yapman gereken adımları sırayla ve kapsamlı olarak özetlemektedir.

### ✅ 1. Ağı Kur: Mininet Topolojisi
- Özel bir ağ topolojisi oluşturulmalı.
- Topolojide:
  - 1 adet **border switch (S1)**,
  - 2-3 adet **intermediate/core switch (S2–S4)**,
  - 3 adet **leaf switch (S5–S7)**,
  - 4 adet **video server (Server1–4)**,
  - En az 1 adet **client** bulunmalı.
- Bu yapı `.py` uzantılı bir Python dosyasında yazılacak (`custom_topo.py`).

---

### ✅ 2. Kontrolcü (Controller) Yaz: Trafiği Yönlendir
- **POX** veya **Ryu** gibi bir SDN controller kullan.
- Bu controller:
  - DNS gibi davranarak gelen istekleri yakalayacak (örnek: netflix.com).
  - Gelen isteğin hangi server’a yönlendirileceğine karar verecek.
  - Kararına göre ağ üzerindeki switch’lere **flow rule** yazacak.

---

### ✅ 3. Load Balancer Uygula: Yük Paylaştırma
- Controller içinde bir load balancing algoritması kullanılacak:
  - `Random`
  - `Round Robin`
  - `Weighted Round Robin`
  - `Bandwidth-Aware`
  - `Request Demand Based`
- Her yeni istemci isteği, seçilen algoritmaya göre en uygun sunucuya yönlendirilecek.

---

### ✅ 4. Video Streaming Simülasyonu Kur
- Her sunucu üzerinde Python ile küçük bir HTTP server aç (`python3 -m http.server`).
- Client node, video talebini örneğin `curl` veya `wget` ile başlatacak.
- Streaming sırasında trafik controller tarafından yönlendirilecek.

---

### ✅ 5. Dashboard veya Loglama Sistemi Oluştur (Opsiyonel ama Faydalı)
- Topolojiyi ve trafiği gözlemlemek için küçük bir monitoring arayüzü yapabilirsin:
  - Aktif sunucular
  - Sunucuların yük durumu
  - Trafik yoğunluğu (hangi client, hangi sunucu ile ne kadar veri aktardı)

---

### ✅ 6. Rapor Yaz ve Sunuma Hazırlan
- Projenin son adımı olarak:
  - Kullandığın mimariyi anlatan bir **rapor** yaz.
  - Kodu ve çıktılarını (ekran görüntüleri dahil) ekle.
  - Hangi algoritmayı neden seçtiğini açıkla.
  - Zorlukları ve çözümleri anlat.

---

## 🧠 Bölüm 2 – Nasıl Yapacağım? (Diller, Araçlar, İpuçları)

Bu bölümde her bileşenin nasıl geliştirileceğini, hangi dillerle yazılacağını ve nelere dikkat etmen gerektiğini öğrenebilirsin.

---

### 🔧 Kullanılacak Diller ve Araçlar

| Bileşen                  | Dil / Araç                         |
|--------------------------|------------------------------------|
| Ağ Topolojisi            | Python (Mininet API)              |
| SDN Controller           | Python (POX veya Ryu)             |
| Load Balancer            | Python                            |
| Video Sunucular          | Python (`http.server`)            |
| Client Testleri          | Bash (`curl`, `wget`, `iperf`)    |
| Dashboard (Opsiyonel)    | Python (Flask, Dash) veya HTML/JS |

---

### 🗂 Proje Dosya Yapısı Önerisi

```

sdn-video-streaming-project/
│
├── topo/
│   └── custom\_topo.py              # Mininet topolojisi
│
├── controller/
│   └── sdn\_controller.py           # Controller + Load Balancer
│
├── servers/
│   ├── server1/
│   │   └── video.mp4
│   └── ...
│
├── client/
│   └── test\_client.sh              # curl ile test scriptleri
│
├── dashboard/                      # Opsiyonel izleme
│   └── monitor.py
│
├── logs/
│   └── traffic\_log.txt             # Trafik kayıtları
│
└── README.md                       # Bu döküman

```

---

### ⚠️ Dikkat Edilmesi Gerekenler

1. **Flow Control**:
   - Controller’ın her yeni bağlantı için doğru akış kuralını (`flow rule`) yüklemesi gerekiyor.
   - Test için `dpctl dump-flows` veya Ryu GUI REST API kullanılabilir.

2. **Bağlantı Testi**:
   - Sunucu ve istemciler arası bağlantıyı `ping`, `iperf`, `curl` ile test et.
   - Trafik yönlendirmesinin doğru olup olmadığını Wireshark veya `tcpdump` ile gözlemle.

3. **Algoritma Seçimi**:
   - En basit algoritma: `round robin`
   - Gelişmiş için: Bant genişliği ölç (iperf), cevap süresine göre seçim yap

4. **Zaman Yönetimi**:
   - Projeye mümkünse önce topolojiden başla, sonra controller ve en son load balancer.
   - Dashboard'u en son yap (zaman kalırsa).

---

### ✅ Önerilen Geliştirme Sırası

1. Mininet ile topolojiyi oluştur.
2. Python controller’ı yaz ve POX/Ryu üzerinde çalıştır.
3. Load balancing algoritmasını entegre et.
4. HTTP sunucuları kur ve test bağlantıları yap.
5. Dashboard veya log sistemi ekle (isteğe bağlı).
6. Rapor ve sunumu hazırla.

---

### 👨‍💻 Kaynaklar

- [Mininet Guide](http://mininet.org/walkthrough/)
- [POX Documentation](https://openflow.stanford.edu/display/ONL/POX+Wiki)
- [Ryu SDN Framework](https://osrg.github.io/ryu/)
- [Python http.server](https://docs.python.org/3/library/http.server.html)

---

**Good luck! You’re building a real SDN-based service routing system 🚀**
```

---

İstersen bu dosyayı `.md` formatında dışa aktarman veya bir IDE'ye yapıştırarak kullanman için sana uygun hale getirebilirim. Ayrıca her bir bölüm için örnek kodlarla birlikte ilerlemek istersen sırayla yardım edebilirim. Hangi bölümden başlamak istersin?
