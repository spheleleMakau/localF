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
