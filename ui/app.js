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
const themeToggleButton = document.querySelector("#themeToggle");
const autocompleteList = document.querySelector("#autocomplete-list");
let debounceTimer;

// Check for saved user preference on load
if (localStorage.getItem("wanderwise_theme") === "light") {
  document.body.classList.add("light-theme");
  if (themeToggleButton) themeToggleButton.textContent = "🌙 Dark";
}

if (themeToggleButton) {
  themeToggleButton.addEventListener("click", () => {
    document.body.classList.toggle("light-theme");
    const isLight = document.body.classList.contains("light-theme");

    themeToggleButton.textContent = isLight ? "🌙 Dark" : "☀️ Light";
    localStorage.setItem("wanderwise_theme", isLight ? "light" : "dark");
  });
}

// Location Autocomplete Event Listener
locationInput.addEventListener("input", function () {
  const query = this.value.trim();
  clearTimeout(debounceTimer);

  if (query.length < 3) {
    if (autocompleteList) autocompleteList.style.display = "none";
    return;
  }

  debounceTimer = setTimeout(async () => {
    try {
      // Fetching autocomplete predictions from Geoapify publicly or via a backend route
      // If your key is strictly backend-only, you can create a lightweight /api/autocomplete route.
      const response = await fetch(
        `/api/autocomplete?query=${encodeURIComponent(query)}`,
      );
      const data = await response.json();

      if (autocompleteList) {
        autocompleteList.innerHTML = "";
        if (data.results && data.results.length > 0) {
          data.results.forEach((place) => {
            const item = document.createElement("div");
            item.className = "autocomplete-item";
            item.textContent = place.formatted;

            item.addEventListener("click", () => {
              locationInput.value = place.formatted;
              autocompleteList.style.display = "none";
            });

            autocompleteList.appendChild(item);
          });
          autocompleteList.style.display = "block";
        } else {
          autocompleteList.style.display = "none";
        }
      }
    } catch (err) {
      console.error("Autocomplete fetch error:", err);
    }
  }, 300);
});

document.addEventListener("click", function (e) {
  if (
    autocompleteList &&
    !locationInput.contains(e.target) &&
    !autocompleteList.contains(e.target)
  ) {
    autocompleteList.style.display = "none";
  }
});

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

  try {
    const rawLocation = locationInput.value.trim() || "Bengaluru";
    const selectedVibe =
      vibeSelect.value === "Select" ? "nature" : vibeSelect.value;
    const requestedDays = Math.min(
      14,
      Math.max(1, Number.parseInt(daysInput.value, 10) || 1),
    );

    const response = await fetch("/api/itinerary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: rawLocation,
        location: rawLocation,
        vibe: selectedVibe,
        days: requestedDays,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server returned status ${response.status}`);
    }

    const result = await response.json();

    let recText =
      result.final_recommendation ||
      "Here is your customized travel itinerary.";
    if (Array.isArray(recText)) {
      recText = recText
        .map((item) =>
          typeof item === "object" ? item.text || JSON.stringify(item) : item,
        )
        .join(" ");
    } else if (typeof recText === "object" && recText !== null) {
      recText = recText.text || JSON.stringify(recText);
    }

    renderItinerary({
      location: rawLocation,
      vibe: selectedVibe,
      structuredPlan: result.structured_plan || {},
      recommendationText: recText,
    });
  } catch (error) {
    console.error("Failed to fetch itinerary:", error);
    alert(
      "Something went wrong while generating your itinerary. Please check your backend logs.",
    );
  } finally {
    submitButton.classList.remove("loading");
    submitButton.disabled = false;
  }
});

function renderItinerary({
  location,
  vibe,
  structuredPlan,
  recommendationText,
}) {
  const isCoordinates = /^[0-9.,\s-]+$/.test(location);
  const destination = isCoordinates
    ? "Nearby"
    : location.split(",")[0].trim() || "Your";

  const dayKeys = Object.keys(structuredPlan);
  let activeDay = 0;

  heroTitle.textContent = `Your ${destination} Adventure`;
  heroBadges.innerHTML = `<span class="badge">${capitalize(vibe)} vibe</span><span class="badge">${dayKeys.length} ${dayKeys.length === 1 ? "day" : "days"}</span>`;

  finalRecommendation.textContent =
    typeof recommendationText === "string"
      ? recommendationText
      : JSON.stringify(recommendationText);

  function renderTabs() {
    dayTabs.innerHTML = dayKeys
      .map(
        (dayKey, index) =>
          `<button class="day-tab ${index === activeDay ? "active" : ""}" type="button" role="tab" aria-selected="${index === activeDay}" data-day="${index}">${dayKey}</button>`,
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
    const currentKey = dayKeys[activeDay];
    const stops = structuredPlan[currentKey] || [];
    timeline.innerHTML = stops.length
      ? stops.map((stop, index) => itineraryCard(stop, index)).join("")
      : `<div class="empty-day"><h3>Free day</h3><p>Use this day to explore at your own pace.</p></div>`;
  }

  renderTabs();
  renderCards();
  emptyState.style.display = "none";
  resultHero.classList.add("show");
  if (window.matchMedia("(max-width: 960px)").matches)
    resultHero.scrollIntoView({ behavior: "smooth", block: "start" });
}

function itineraryCard(stop, index) {
  const name = escapeHtml(stop.name || stop.title || "Stop");
  const address = escapeHtml(
    stop.address || stop.vicinity || "Address unavailable",
  );
  let rawDistance =
    stop.distance_meters !== undefined ? stop.distance_meters : stop.distance;
  let distance = "";
  if (rawDistance !== undefined && rawDistance !== null) {
    const km = (Number(rawDistance) / 1000).toFixed(1);
    distance = `${km} km away`;
  }

  const category = escapeHtml(stop.category || "Recommended Stop");

  return `<article class="itinerary-card">
    <div class="stop-index">${index + 1}</div>
    <div class="card-main">
      <div class="card-header-row">
        <h3>${name}</h3>
        <div class="card-tags">
          <span>${distance}</span>
        </div>
      </div>
      <p class="stop-address">${address}</p>

      <p class="stop-description">${category}</p>

      <div class="card-actions" style="margin-top: 12px;">
        <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(name + " " + address)}" target="_blank" rel="noopener">Get directions</a>
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
