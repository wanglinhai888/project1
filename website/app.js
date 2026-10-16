/* AI 大模型价格雷达 - 网站逻辑（Vue3 + ECharts）
 * 数据来源：data/today.json（爬虫实时真实价）、data/history.json、data/promotions.json
 * 主价格表展示 today.json，每行标注 source：openrouter_api/official=真实价，fallback=国内直连参考
 */
const { createApp } = Vue;

const CURRENCY_SYMBOL = { USD: "$", CNY: "¥" };
const MODEL_SEP = " · ";

const I18N = {
  zh: {
    appTitle: "AI 大模型价格雷达",
    subtitle: "自动追踪全球大模型 API 价格变化",
    updatedAt: "数据更新于",
    loading: "数据加载中...",
    tabPrice: "价格",
    tabPromo: "优惠",
    tabTools: "工具指南",
    providers: "覆盖厂商",
    models: "监控模型",
    priceDown: "今日降价",
    priceUp: "今日涨价",
    newModels: "新模型",
    changesTitle: "今日价格变化",
    noChanges: "今日暂无价格变化，所有模型价格保持稳定。",
    promoTitle: "优惠活动",
    noPromo: "暂无优惠活动信息。",
    priceTableTitle: "实时价格表",
    viewChanged: "仅看变动",
    viewAll: "全部模型",
    searchPlaceholder: "搜索模型 / 厂商...",
    allProviders: "全部厂商",
    thPlatform: "平台",
    thModel: "代表模型",
    thInput: "输入 (每百万)",
    thOutput: "输出 (每百万)",
    thContext: "上下文窗口",
    thSource: "来源",
    thOfficial: "官网",
    noChanged: "今日暂无价格变动。可切换到「全部模型」查看全部 {0} 个模型。",
    modelsSuffix: "个模型",
    allModelsEmpty: "没有匹配的模型，换个关键词试试。",
    expand: "展开",
    collapse: "收起",
    unitNote: "价格为每百万 Token（1M tokens）。<span class=\"source official\">真实API</span> 来自 OpenRouter 官方接口实时价，<span class=\"source official\">官网抓取</span> 为厂商官网直采；<span class=\"source fallback\">国内直连参考</span> 为官网不可达时的参考价，实际请以厂商官网为准。",
    trendTitle: "价格趋势",
    trendHint: "历史数据正在积累中，每日自动采集后将生成趋势曲线。",
    toolsTitle: "工具指南",
    noTools: "暂无工具指南内容。",
    toolPrice: "价格 / 套餐",
    srcLink: "来源 ↗",
    officialLink: "官网 ↗",
    openrouterLink: "OpenRouter ↗",
    pagerFirst: "« 首页",
    pagerPrev: "‹ 上一页",
    pagerNext: "下一页 ›",
    pagerLast: "末页 »",
    pagerPage: "第 {0} / {1} 页",
    footer1: "数据来源：OpenRouter 官方 API 实时价（覆盖主流及国内厂商转售价）+ 各厂商官网直采；每日由 GitHub Actions 自动更新。",
    footer2: "绿色「真实API / 官网抓取」为实时采集价；黄色「国内直连参考」为官网不可达时的参考价，请以厂商官网为准。",
    type_price_up: "涨价",
    type_price_down: "降价",
    type_new_model: "新模型",
    src_openrouter_api: "真实API",
    src_official: "官网抓取",
    src_fallback: "国内直连参考"
  },
  en: {
    appTitle: "AI Model Price Radar",
    subtitle: "Auto-tracking global LLM API price changes",
    updatedAt: "Updated",
    loading: "Loading...",
    tabPrice: "Prices",
    tabPromo: "Promotions",
    tabTools: "Tool Guide",
    providers: "Providers",
    models: "Models",
    priceDown: "Price Drops",
    priceUp: "Price Hikes",
    newModels: "New Models",
    changesTitle: "Today's Price Changes",
    noChanges: "No price changes today; all models remain stable.",
    promoTitle: "Promotions",
    noPromo: "No promotion info yet.",
    priceTableTitle: "Live Price Table",
    viewChanged: "Changes only",
    viewAll: "All models",
    searchPlaceholder: "Search model / provider...",
    allProviders: "All providers",
    thPlatform: "Platform",
    thModel: "Model",
    thInput: "Input (per 1M)",
    thOutput: "Output (per 1M)",
    thContext: "Context",
    thSource: "Source",
    thOfficial: "Site",
    noChanged: "No price changes today. Switch to “All models” to view all {0} models.",
    modelsSuffix: "models",
    allModelsEmpty: "No matching models. Try another keyword.",
    expand: "Expand",
    collapse: "Collapse",
    unitNote: "Prices per 1M tokens. <span class=\"source official\">Real API</span> from OpenRouter official live prices, <span class=\"source official\">Official</span> scraped from vendor sites; <span class=\"source fallback\">Domestic ref</span> is a fallback when the site is unreachable — refer to the vendor's site.",
    trendTitle: "Price Trend",
    trendHint: "History is accumulating; daily auto-collection will generate trend curves.",
    toolsTitle: "Tool Guide",
    noTools: "No tool guide content yet.",
    toolPrice: "Pricing",
    srcLink: "Source ↗",
    officialLink: "Official ↗",
    openrouterLink: "OpenRouter ↗",
    pagerFirst: "« First",
    pagerPrev: "‹ Prev",
    pagerNext: "Next ›",
    pagerLast: "Last »",
    pagerPage: "Page {0} / {1}",
    footer1: "Data: OpenRouter official API live prices (covering mainstream & domestic resale) + vendor official sites; auto-updated daily via GitHub Actions.",
    footer2: "Green “Real API / Official” are live collected prices; yellow “Domestic ref” is a fallback when the official site is unreachable — refer to the vendor's site.",
    type_price_up: "Up",
    type_price_down: "Down",
    type_new_model: "New",
    src_openrouter_api: "Real API",
    src_official: "Official",
    src_fallback: "Domestic ref"
  }
};

createApp({
  data() {
    return {
      today: null,
      history: [],
      promotions: [],
      tools: [],
      activeTab: "price",
      lang: "zh",
      loading: true,
      error: "",
      keyword: "",
      providerFilter: "",
      selectedModel: "",
      chart: null,
      viewMode: "changed",
      collapsed: {},
      pages: {},
      pageSize: 20,
    };
  },
  computed: {
    tableProviders() {
      if (!this.today) return [];
      return [...new Set(this.today.prices.map((p) => p.provider))].sort();
    },
    filteredTable() {
      if (!this.today) return [];
      const kw = this.keyword.trim().toLowerCase();
      return this.today.prices.filter((p) => {
        const okKw =
          !kw ||
          p.model.toLowerCase().includes(kw) ||
          p.provider.toLowerCase().includes(kw);
        const okProvider = !this.providerFilter || p.provider === this.providerFilter;
        return okKw && okProvider;
      });
    },
    modelOptions() {
      if (!this.today) return [];
      return this.today.prices.map((p) => p.provider + MODEL_SEP + p.model);
    },
    changedSet() {
      if (!this.today) return new Set();
      const s = new Set();
      (this.today.changes || []).forEach((c) => s.add(c.provider + "||" + c.model));
      return s;
    },
    changedModels() {
      if (!this.today) return [];
      return this.filteredTable.filter((p) =>
        this.changedSet.has(p.provider + "||" + p.model)
      );
    },
    groupedAll() {
      if (!this.today) return [];
      const map = new Map();
      this.filteredTable.forEach((p) => {
        if (!map.has(p.provider)) map.set(p.provider, []);
        map.get(p.provider).push(p);
      });
      return [...map.entries()].map(([provider, models]) => ({ provider, models }));
    },
    trendHint() {
      if (!this.selectedModel) return "";
      const [provider, model] = this.selectedModel.split(MODEL_SEP);
      const count = this.history.filter(
        (h) => h.provider === provider && h.model === model
      ).length;
      if (count < 2) return this.t("trendHint");
      return "";
    },
  },
  watch: {
    selectedModel() {
      this.renderChart();
    },
  },
  async mounted() {
    try {
      const [today, history, promotions, tools] = await Promise.all([
        this.loadJSON("data/today.json"),
        this.loadJSON("data/history.json"),
        this.loadJSON("data/promotions.json?v=8"),
        this.loadJSON("data/tools.json?v=9"),
      ]);
      this.today = today;
      this.history = Array.isArray(history) ? history : [];
      this.promotions = Array.isArray(promotions) ? promotions : [];
      this.tools = Array.isArray(tools) ? tools : [];
      if (this.today.changes && this.today.changes.length) {
        this.viewMode = "changed";
      } else {
        this.viewMode = "all";
      }
      if (this.modelOptions.length) this.selectedModel = this.modelOptions[0];
      this.$nextTick(() => this.renderChart());
    } catch (e) {
      this.error = "数据加载失败：" + e.message;
      console.error(e);
    } finally {
      this.loading = false;
    }
  },
  methods: {
    async loadJSON(path) {
      const resp = await fetch(path);
      if (!resp.ok) {
        if (resp.status === 404) return [];
        throw new Error(path + " " + resp.status);
      }
      return resp.json();
    },
    typeText(type) {
      return this.t("type_" + type) || type;
    },
    sourceText(source) {
      return this.t("src_" + source) || source;
    },
    sourceClass(source) {
      return source === "openrouter_api" || source === "official" ? "official" : "fallback";
    },
    isOpenRouterPage(url) {
      return typeof url === "string" && url.indexOf("openrouter.ai") !== -1;
    },
    setTab(name) {
      this.activeTab = name;
      if (name === "price") {
        this.$nextTick(() => this.renderChart());
      }
    },
    setLang(l) {
      this.lang = l;
      document.documentElement.lang = l === "en" ? "en" : "zh-CN";
      document.title = l === "en" ? "AI Model Price Radar" : "AI 大模型价格雷达";
      if (this.activeTab === "price") {
        this.$nextTick(() => this.renderChart());
      }
    },
    t(key, ...args) {
      const dict = I18N[this.lang] || I18N.zh;
      let s = dict[key];
      if (s === undefined) s = I18N.zh[key] !== undefined ? I18N.zh[key] : key;
      if (args.length) {
        args.forEach((a, i) => { s = String(s).replace("{" + i + "}", a); });
      }
      return s;
    },
    lng(obj, key) {
      if (!obj) return "";
      const k = key + (this.lang === "en" ? "_en" : "");
      return obj[k] !== undefined && obj[k] !== "" ? obj[k] : obj[key];
    },
    contextText(n) {
      if (!n) return "-";
      if (n >= 1000000) return (n / 1000000).toFixed(0) + "M";
      if (n >= 1000) return (n / 1000).toFixed(0) + "K";
      return String(n);
    },
    priceText(price, currency) {
      const sym = CURRENCY_SYMBOL[currency] || currency + " ";
      if (price === 0) return sym + "0";
      return sym + price.toFixed(price < 1 ? 3 : 2);
    },
    toggleCollapse(provider) {
      this.collapsed[provider] = !this.collapsed[provider];
    },
    isCollapsed(provider) {
      return !!this.collapsed[provider];
    },
    currentPage(group) {
      return this.pages[group.provider] || 1;
    },
    totalPages(group) {
      return Math.max(1, Math.ceil(group.models.length / this.pageSize));
    },
    pagedModels(group) {
      const start = (this.currentPage(group) - 1) * this.pageSize;
      return group.models.slice(start, start + this.pageSize);
    },
    setPage(group, page) {
      const t = this.totalPages(group);
      this.pages[group.provider] = Math.min(Math.max(1, page), t);
    },
    renderChart() {
      if (!this.chart) {
        const el = document.getElementById("trendChart");
        if (el) this.chart = echarts.init(el);
      }
      if (!this.chart || !this.selectedModel) return;
      const [provider, model] = this.selectedModel.split(MODEL_SEP);
      const records = this.history
        .filter((h) => h.provider === provider && h.model === model)
        .sort((a, b) => a.date.localeCompare(b.date));
      const option = {
        tooltip: { trigger: "axis" },
        legend: {
          data: ["输入价格", "输出价格"],
          textStyle: { color: "#9fb3c8" },
        },
        grid: { left: 64, right: 24, top: 44, bottom: 40 },
        xAxis: {
          type: "category",
          data: records.map((r) => r.date),
          axisLabel: { color: "#9fb3c8" },
          axisLine: { lineStyle: { color: "#2a3b52" } },
        },
        yAxis: {
          type: "value",
          name: "价格 / 百万Token",
          nameTextStyle: { color: "#9fb3c8" },
          axisLabel: { color: "#9fb3c8" },
          splitLine: { lineStyle: { color: "#1e2a3a" } },
        },
        series: [
          {
            name: "输入价格",
            type: "line",
            smooth: true,
            symbolSize: 7,
            data: records.map((r) => r.input_price),
            itemStyle: { color: "#4ade80" },
            lineStyle: { width: 2.5 },
          },
          {
            name: "输出价格",
            type: "line",
            smooth: true,
            symbolSize: 7,
            data: records.map((r) => r.output_price),
            itemStyle: { color: "#60a5fa" },
            lineStyle: { width: 2.5 },
          },
        ],
      };
      this.chart.setOption(option, true);
    },
  },
}).mount("#app");
