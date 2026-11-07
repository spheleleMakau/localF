const menuToggle = document.querySelector("[data-menu-toggle]");
const navigation = document.querySelector("[data-navigation]");

if (menuToggle && navigation) {
  document.documentElement.classList.add("js-menu");
  const closeMenu = () => {
    menuToggle.setAttribute("aria-expanded", "false");
    navigation.classList.remove("is-open");
  };
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    navigation.classList.toggle("is-open", !expanded);
  });
  navigation.addEventListener("click", (event) => {
    if (event.target.closest("a")) closeMenu();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") {
      closeMenu();
      menuToggle.focus();
    }
  });
  window.matchMedia("(max-width: 900px)").addEventListener("change", closeMenu);
}

for (const [containerSelector, slideSelector] of [
  ["[data-model-slideshow]", "[data-model-slide]"],
  ["[data-entertainer-slideshow]", "[data-entertainer-slide]"],
]) {
  const slideshow = document.querySelector(containerSelector);
  if (!slideshow) continue;
  const slides = [...slideshow.querySelectorAll(slideSelector)];
  if (slides.length > 1 && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    let active = 0;
    window.setInterval(() => {
      slides[active].hidden = true;
      active = (active + 1) % slides.length;
      slides[active].hidden = false;
    }, 3000);
  }
}
