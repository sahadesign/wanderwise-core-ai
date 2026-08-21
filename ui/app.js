const vibeSelect = document.querySelector("#vibe");
const geoButton = document.querySelector("#geoBtn");
const geoStatus = document.querySelector("#geoStatus");
const locationInput = document.querySelector("#location");
const daysInput = document.querySelector("#days");
const form = document.querySelector("#tripForm");
const submitButton = document.querySelector("#submitBtn");
const emptyState = document.querySelector("#emptyState");
const resultHero = document.querySelector("#resultHero");
const heroTitle = document.querySelector("#heroTitle");
const heroBadges = document.querySelector("#heroBadges");
const dayTabs = document.querySelector("#dayTabs");
const timeline = document.querySelector("#timeline");
const finalRecommendation = document.querySelector("#finalRec");
const resetButton = document.querySelector("#resetBtn");

const demoStops = [
  {
    name: "Sunrise Botanical Garden",
    address: "18 Garden Lane, City Centre",
    category: "Nature & Gardens",
    description:
      "Wander in before the crowds arrive, when the paths are quiet and the light is soft. Wide lawns give way to shaded groves and a small pond where locals do their morning tai chi. It's the kind of place that resets your pace before the rest of the day picks up.",
    price: "Free",
    duration: "1.5h",
  },
  {
    name: "Old Town Market",
    address: "42 Market Street, City Centre",
    category: "Culture & Shopping",
    description:
      "A tangle of narrow lanes packed with fabric stalls, spice vendors, and family-run stands that have been here for generations. Haggling is half the fun, and even if you don't buy anything, the smells and noise alone are worth the detour. Grab a snack from one of the corner carts while you browse.",
    price: "Approx. $10-20",
    duration: "1h",
  },
  {
    name: "Heritage Museum",
    address: "7 Museum Square, City Centre",
    category: "History & Culture",
    description:
      "Housed in a restored 19th-century building, the museum walks you through the city's founding, its trade routes, and the everyday objects that tell those stories better than any plaque. The top floor has a rotating exhibit worth checking before you go, and the courtyard cafe is a good spot to sit with your thoughts afterward.",
    price: "$12 entry",
    duration: "1.5h",
  },
  {
    name: "Artisan District",
    address: "85 Studio Road, City Centre",
    category: "Art & Design",
    description:
      "Cobbled streets lined with working studios where you can watch potters, printmakers, and jewelers at their benches. Most doors are open to browsers, and a few offer short hands-on demos if you ask. Slow down here — there's no single must-see stop, just a lot of small, worthwhile detours.",
    price: "Free to explore",
    duration: "1.5h",
  },
  {
    name: "Lantern Street",
    address: "Lantern Street, City Centre",
    category: "Evening Walk",
    description:
      "As the sun drops, strings of paper lanterns flicker on above the street and the whole block turns into a slow-moving crowd of food stalls, buskers, and photo stops. It's louder and more crowded than earlier in the day, but that's the appeal — this is where the city comes out to unwind.",
    price: "Free",
    duration: "1h",
  },
  {
    name: "Riverside Promenade",
    address: "River Walk, City Centre",
    category: "Scenic Walk",
    description:
      "A long, flat path that hugs the water, popular with joggers and cyclists early in the day. Benches are spaced out every few hundred meters if you want to stop and watch the boats go by, and there's a small kiosk about halfway along selling coffee and pastries.",
    price: "Free",
    duration: "1h",
  },
  {
    name: "Local Coffee House",
    address: "12 Willow Street, City Centre",
    category: "Food & Drink",
    description:
      "A tiny, plant-filled spot with mismatched chairs and a menu that changes with the seasons. The house blend is roasted upstairs, and the pastry case is usually cleared out by early afternoon, so this is a good mid-morning stop rather than a lunch one.",
    price: "Approx. $8-15",
    duration: "45m",
  },
  {
    name: "Skyline Viewpoint",
    address: "Hillcrest Avenue, City Centre",
    category: "Viewpoint",
    description:
      "A short, steady climb up a series of switchback stairs rewards you with a full panorama of the city and, on clear days, the hills beyond it. There's a low wall to sit on and a couple of vendors selling cold drinks near the top, so no need to rush back down.",
    price: "Free",
    duration: "1h",
  },
  {
    name: "Harbour Food Hall",
    address: "3 Harbour Place, City Centre",
    category: "Dining",
    description:
      "A converted warehouse now packed with a dozen small kitchens, each specializing in one or two dishes done well. Grab a table by the open windows facing the water, order from a few different stalls, and let the meal stretch out — this is meant to be lingered over, not rushed.",
    price: "Approx. $15-30",
    duration: "1.5h",
  },
];

geoButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    geoStatus.textContent = "Geolocation is not supported";
    return;
  }
  geoStatus.textContent = "Locating...";
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      locationInput.value = `${coords.latitude.toFixed(4)},${coords.longitude.toFixed(4)}`;
      geoStatus.textContent = "Location set";
    },
    () => {
      geoStatus.textContent = "Could not get location - enter it manually";
    },
  );
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.classList.add("loading");
  submitButton.disabled = true;
  await new Promise((resolve) => setTimeout(resolve, 450));
  renderItinerary({
    location: locationInput.value.trim() || "Bengaluru",
    vibe: vibeSelect.value === "Select" ? "nature" : vibeSelect.value,
    days: Math.min(14, Math.max(1, Number.parseInt(daysInput.value, 10) || 1)),
  });
  submitButton.classList.remove("loading");
  submitButton.disabled = false;
});

function renderItinerary({ location, vibe, days }) {
  const destination = location.split(",")[0].trim() || "Your";
  const daysPlan = distributeStops(days);
  let activeDay = 0;
  heroTitle.textContent = `Your ${destination} Adventure`;
  heroBadges.innerHTML = `<span class="badge">${capitalize(vibe)} vibe</span><span class="badge">${days} ${days === 1 ? "day" : "days"}</span><span class="badge">Demo itinerary</span>`;
  finalRecommendation.textContent =
    "A balanced route with room to wander, pause, and follow the moments that feel right.";

  function renderTabs() {
    dayTabs.innerHTML = daysPlan
      .map(
        (stops, index) =>
          `<button class="day-tab ${index === activeDay ? "active" : ""}" type="button" role="tab" aria-selected="${index === activeDay}" data-day="${index}">Day ${index + 1}</button>`,
      )
      .join("");
    dayTabs.querySelectorAll("button").forEach((button) =>
      button.addEventListener("click", () => {
        activeDay = Number(button.dataset.day);
        renderTabs();
        renderCards();
      }),
    );
  }

  function renderCards() {
    const stops = daysPlan[activeDay];
    timeline.innerHTML = stops.length
      ? stops.map((stop, index) => itineraryCard(stop, index)).join("")
      : `<div class="empty-day"><h3>Free day</h3><p>Use this day to revisit a favorite place or explore at your own pace.</p></div>`;
  }

  renderTabs();
  renderCards();
  emptyState.style.display = "none";
  resultHero.classList.add("show");
  if (window.matchMedia("(max-width: 960px)").matches)
    resultHero.scrollIntoView({ behavior: "smooth", block: "start" });
}

function distributeStops(days) {
  return Array.from({ length: days }, (_, index) => {
    const start = Math.floor((index * demoStops.length) / days);
    const end = Math.floor(((index + 1) * demoStops.length) / days);
    return demoStops.slice(start, end);
  });
}

function itineraryCard(stop, index) {
  const name = escapeHtml(stop.name);
  const address = escapeHtml(stop.address);
  return `<article class="itinerary-card">
    <div class="stop-index">${index + 1}</div>
    <div class="card-main">
      <div class="card-header-row">
        <h3>${name}</h3>
        <div class="card-tags">
          <span>${escapeHtml(stop.price)}</span>
          <span>${escapeHtml(stop.duration)}</span>
        </div>
      </div>
      <p class="stop-address">Location: ${address}</p>
      <p class="stop-description">${escapeHtml(stop.category)} - ${escapeHtml(stop.description)}</p>
      <div class="card-actions">
        <a href="#" target="_blank" rel="noopener">Get directions</a>
        <button type="button" data-place="${name}">View details</button>
      </div>
    </div>
  </article>`;
}

resetButton.addEventListener("click", () => {
  resultHero.classList.remove("show");
  emptyState.style.display = "flex";
  form.reset();
  geoStatus.textContent = "";
});

function capitalize(value) {
  return value ? value[0].toUpperCase() + value.slice(1) : "";
}
function escapeHtml(value) {
  return String(value).replace(
    /[&<>'"]/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[
        character
      ],
  );
}

// Auto-load a default demo itinerary on page load for testing
window.addEventListener("DOMContentLoaded", () => {
  renderItinerary({
    location: "Bengaluru",
    vibe: "nature",
    days: 1,
  });
});
