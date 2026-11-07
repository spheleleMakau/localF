const trainingShop = document.querySelector("[data-training-shop]");

if (trainingShop) {
  const city = trainingShop.querySelector('[name="city"]');
  const otherCity = trainingShop.querySelector("[data-other-city]");
  const otherCityInput = trainingShop.querySelector('[name="other_city"]');
  const training = trainingShop.querySelector('[name="training"]');
  const hours = trainingShop.querySelector("[data-training-hours]");
  const hoursInput = trainingShop.querySelector('[name="hours"]');
  const otherOption = city.querySelector('option[value="other"]');
  const page = trainingShop.closest("[data-training-shop-page]");

  const updateTraining = () => {
    const individual = training.value === "individual";
    page.querySelectorAll("[data-training-details], [data-city-help]").forEach((element) => {
      const type = element.dataset.trainingDetails || element.dataset.cityHelp;
      element.hidden = type !== training.value;
    });
    hours.hidden = !individual;
    hoursInput.disabled = !individual;
    hoursInput.required = individual;
    otherOption.hidden = !individual;
    otherOption.disabled = !individual;
    const show = city.value === "other" && individual;
    otherCity.hidden = !show;
    otherCityInput.required = show;
  };

  city.addEventListener("change", updateTraining);
  training.addEventListener("change", () => {
    if (training.value === "course" && city.value === "other") city.value = "";
    updateTraining();
  });
  updateTraining();
}
