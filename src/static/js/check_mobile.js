document.addEventListener("alpine:init", () => {
  Alpine.store("screen", {
    isMobile: false,

    init() {
      const query = window.matchMedia("(max-width: 767px)");

      this.isMobile = query.matches;

      query.addEventListener("change", (e) => {
        this.isMobile = e.matches;
      });
    },
  });
});
