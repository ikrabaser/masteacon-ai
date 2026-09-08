import type { Locale } from "./translations";

const en = {
  seo: {
    title: "Masteacon — Trusted answers from your knowledge",
    description:
      "Masteacon brings your documents together so your team can ask questions in plain language and get answers backed by visible sources.",
  },

  nav: {
    features: "Features",
    howItWorks: "How it works",
    security: "Security",
    signIn: "Sign in",
    getStarted: "Get started",
    explore: "MENU",
    openMenu: "Open navigation",
    closeMenu: "Close navigation",
  },

  hero: {
    eyebrow: "KNOWLEDGE INTELLIGENCE",
    titleStart: "Turn scattered knowledge into",
    titleAccent: " trusted answers.",
    description:
      "Upload your documents, ask questions in plain language, and get concise answers with the exact passages they came from — so you can verify every claim in seconds.",
    primary: "Get started free",
    secondary: "See how it works",
    signals: ["No credit card required", "Free to try"],
  },

  mockup: {
    workspaceLabel: "Employee Handbook",
    question: "How many days of annual leave do I get?",
    answerLabel: "Answer",
    answerTitle: "14 days per year, prorated in your first year.",
    sourceLabel: "Sources",
    sources: ["employee-handbook.pdf, p. 12", "hr-policy.docx, p. 3"],
  },

  features: {
    eyebrow: "WHAT IT DOES",
    title: "Everything a knowledge assistant should be — and nothing it shouldn't.",
    items: [
      {
        icon: "search",
        title: "Search by meaning",
        description:
          "Find the right passage even when your question uses different words than the document does.",
      },
      {
        icon: "chat",
        title: "Answers with sources",
        description:
          "Every answer links back to the exact document and passage it's based on, so you can check it yourself.",
      },
      {
        icon: "folder",
        title: "Isolated workspaces",
        description:
          "Keep client work, teams, or projects in separate workspaces — nothing crosses over by accident.",
      },
      {
        icon: "sparkle",
        title: "An agent that can act",
        description:
          "Ask it to look something up, then use what it found to answer a follow-up — all within a bounded, auditable loop.",
      },
    ],
  },

  how: {
    eyebrow: "HOW IT WORKS",
    title: "From documents to trusted answers in three steps.",
    steps: [
      {
        number: "01",
        title: "Add your documents",
        description: "Upload PDFs, Word docs, or plain text into a workspace. Indexing happens in the background.",
      },
      {
        number: "02",
        title: "Ask naturally",
        description: "Type a question the way you'd ask a colleague — no keywords or special syntax required.",
      },
      {
        number: "03",
        title: "Verify and act",
        description: "Read the answer, check the sources it's grounded in, and act on it with confidence.",
      },
    ],
  },

  trust: {
    eyebrow: "SECURITY",
    title: "Built so you can trust what it tells you",
    titleAccent: " — and who can see it.",
    description:
      "Every workspace is isolated at the database level, every answer is grounded in retrieved evidence, and every action an agent takes is checked against your own permissions before it runs.",
    points: [
      "Workspace data is never visible across accounts",
      "Answers are generated only from retrieved context",
      "Every source cited in an answer is independently checkable",
      "Agent tool calls are authorization-checked on every request",
    ],
  },

  faq: {
    eyebrow: "FAQ",
    title: "Before you start",
    items: [
      {
        question: "What is Masteacon?",
        answer:
          "A knowledge assistant: upload your documents and ask questions about them in plain language. Answers are grounded in your own content, with sources you can check.",
      },
      {
        question: "How does it find the right information?",
        answer:
          "It combines semantic (meaning-based) search with keyword matching, so it finds relevant passages even if your question doesn't use the document's exact wording.",
      },
      {
        question: "Can I trust the answers?",
        answer:
          "Every answer cites the specific passages it's based on. If there isn't enough information in your documents to answer confidently, it says so instead of guessing.",
      },
      {
        question: "What file types are supported?",
        answer: "PDF, Word (.docx), and plain text files today.",
      },
      {
        question: "Is my data isolated from other accounts?",
        answer:
          "Yes. Every workspace is scoped at the database level — no query, search, or agent action can ever reach data outside the workspace it was made for.",
      },
    ],
  },

  finalCta: {
    eyebrow: "GET STARTED",
    title: "Your knowledge is already there. Make it usable.",
    button: "Create your workspace",
  },

  footer: {
    description: "Knowledge intelligence for teams who need answers they can trust.",
    product: "Product",
    productLinks: ["Command Center", "Knowledge Library", "Ask Masteacon", "Agent"],
    explore: "Explore",
    exploreLinks: ["Features", "How it works", "Security"],
    signIn: "Sign in",
    create: "Create account",
  },
};

const tr = {
  seo: {
    title: "Masteacon — Bilginizden güvenilir yanıtlar",
    description:
      "Masteacon dokümanlarınızı bir araya getirir; ekibiniz doğal dille soru sorar ve görünür kaynaklara dayanan yanıtlar alır.",
  },

  nav: {
    features: "Özellikler",
    howItWorks: "Nasıl çalışır",
    security: "Güvenlik",
    signIn: "Giriş yap",
    getStarted: "Başla",
    explore: "MENÜ",
    openMenu: "Menüyü aç",
    closeMenu: "Menüyü kapat",
  },

  hero: {
    eyebrow: "BİLGİ ZEKÂSI",
    titleStart: "Dağınık bilgiyi",
    titleAccent: " güvenilir yanıtlara dönüştürün.",
    description:
      "Dokümanlarınızı yükleyin, doğal dille soru sorun ve geldiği pasajlarla birlikte net yanıtlar alın — her iddiayı saniyeler içinde doğrulayın.",
    primary: "Ücretsiz başla",
    secondary: "Nasıl çalıştığını gör",
    signals: ["Kredi kartı gerekmez", "Ücretsiz deneyin"],
  },

  mockup: {
    workspaceLabel: "Çalışan El Kitabı",
    question: "Yıllık izin hakkım kaç gün?",
    answerLabel: "Yanıt",
    answerTitle: "İlk yıl kıst hesaplanmak üzere, yılda 14 gün.",
    sourceLabel: "Kaynaklar",
    sources: ["calisan-el-kitabi.pdf, s. 12", "ik-politikasi.docx, s. 3"],
  },

  features: {
    eyebrow: "NE YAPAR",
    title: "Bir bilgi asistanının olması gereken her şey — olmaması gereken hiçbir şey.",
    items: [
      {
        icon: "search",
        title: "Anlama göre arama",
        description:
          "Sorunuz dokümandakinden farklı kelimeler kullansa bile doğru pasajı bulur.",
      },
      {
        icon: "chat",
        title: "Kaynaklı yanıtlar",
        description:
          "Her yanıt, dayandığı doküman ve pasaja bağlıdır — isterseniz kendiniz kontrol edin.",
      },
      {
        icon: "folder",
        title: "İzole çalışma alanları",
        description:
          "Müşteri işlerini, ekipleri veya projeleri ayrı çalışma alanlarında tutun — hiçbir şey yanlışlıkla karışmaz.",
      },
      {
        icon: "sparkle",
        title: "Harekete geçebilen ajan",
        description:
          "Bir şeyi araştırmasını isteyin, bulduğuyla takip sorusunu yanıtlasın — hepsi sınırlı ve denetlenebilir bir döngüde.",
      },
    ],
  },

  how: {
    eyebrow: "NASIL ÇALIŞIR",
    title: "Dokümandan güvenilir yanıta üç adımda.",
    steps: [
      {
        number: "01",
        title: "Dokümanlarınızı ekleyin",
        description: "PDF, Word veya düz metin yükleyin. İndeksleme arka planda gerçekleşir.",
      },
      {
        number: "02",
        title: "Doğal şekilde sorun",
        description: "Bir meslektaşınıza sorar gibi yazın — anahtar kelime ya da özel bir söz dizimi gerekmez.",
      },
      {
        number: "03",
        title: "Doğrulayın ve harekete geçin",
        description: "Yanıtı okuyun, dayandığı kaynakları kontrol edin ve güvenle ilerleyin.",
      },
    ],
  },

  trust: {
    eyebrow: "GÜVENLİK",
    title: "Size söylediğine",
    titleAccent: " — ve kimin görebildiğine güvenebilmeniz için kuruldu.",
    description:
      "Her çalışma alanı veritabanı seviyesinde izole edilir, her yanıt yalnızca getirilen kanıta dayanır ve bir ajanın attığı her adım çalışmadan önce sizin yetkilerinize göre kontrol edilir.",
    points: [
      "Çalışma alanı verisi hesaplar arasında asla görünmez",
      "Yanıtlar yalnızca getirilen bağlamdan üretilir",
      "Bir yanıtta gösterilen her kaynak bağımsız olarak doğrulanabilir",
      "Ajan araç çağrıları her istekte yetki kontrolünden geçer",
    ],
  },

  faq: {
    eyebrow: "SSS",
    title: "Başlamadan önce",
    items: [
      {
        question: "Masteacon nedir?",
        answer:
          "Bir bilgi asistanı: dokümanlarınızı yükleyin, doğal dille sorular sorun. Yanıtlar kendi içeriğinize dayanır ve kontrol edebileceğiniz kaynaklar taşır.",
      },
      {
        question: "Doğru bilgiyi nasıl bulur?",
        answer:
          "Anlam tabanlı aramayı anahtar kelime eşleşmesiyle birleştirir; sorunuz dokümanın birebir ifadesini kullanmasa bile ilgili pasajları bulur.",
      },
      {
        question: "Yanıtlara güvenebilir miyim?",
        answer:
          "Her yanıt, dayandığı belirli pasajları gösterir. Dokümanlarınızda güvenle yanıt verecek yeterli bilgi yoksa, tahmin etmek yerine bunu açıkça söyler.",
      },
      {
        question: "Hangi dosya türleri destekleniyor?",
        answer: "Şu an için PDF, Word (.docx) ve düz metin dosyaları.",
      },
      {
        question: "Verilerim diğer hesaplardan izole mi?",
        answer:
          "Evet. Her çalışma alanı veritabanı seviyesinde sınırlandırılır — hiçbir sorgu, arama ya da ajan işlemi ait olmadığı çalışma alanının dışına asla ulaşamaz.",
      },
    ],
  },

  finalCta: {
    eyebrow: "BAŞLAYIN",
    title: "Bilginiz zaten var. Onu kullanılabilir hale getirin.",
    button: "Çalışma alanınızı oluşturun",
  },

  footer: {
    description: "Güvenebileceği yanıtlara ihtiyaç duyan ekipler için bilgi zekâsı.",
    product: "Ürün",
    productLinks: ["Komuta Merkezi", "Bilgi Kütüphanesi", "Masteacon'a Sor", "Ajan"],
    explore: "Keşfet",
    exploreLinks: ["Özellikler", "Nasıl çalışır", "Güvenlik"],
    signIn: "Giriş yap",
    create: "Hesap oluştur",
  },
};

export const landingTranslations: Record<Locale, typeof en> = {
  en,
  tr,
};
