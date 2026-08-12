(function () {
  "use strict";

  function parseData(root, selector) {
    var node = root.querySelector(selector);
    if (!node) return null;
    try { return JSON.parse(node.textContent); }
    catch (error) { return null; }
  }

  document.querySelectorAll('[data-viz="integer-rounding"]').forEach(function (root) {
    var data = parseData(root, ".integrality-data");
    var enhanced = root.querySelector(".integrality-enhanced");
    var fallback = root.querySelector(".integrality-fallback");
    var readout = root.querySelector("[data-integrality-readout]");
    var buttons = Array.from(root.querySelectorAll("[data-integrality-step]"));
    if (!data || !enhanced || !fallback || !readout || !buttons.length) return;

    function select(key) {
      var step = data.steps.find(function (item) { return item.key === key; });
      if (!step) return;
      buttons.forEach(function (button) {
        button.setAttribute("aria-pressed", String(button.dataset.integralityStep === key));
      });
      root.querySelectorAll("[data-stage-point]").forEach(function (point) {
        point.classList.toggle("is-current", point.dataset.stagePoint === key);
      });
      readout.dataset.tone = step.tone;
      readout.innerHTML = "<small>" + step.label + "</small><strong>" + step.point
        + "</strong><b>" + step.value + "</b><p>" + step.message + "</p>";
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () { select(button.dataset.integralityStep); });
    });
    fallback.hidden = true;
    enhanced.hidden = false;
    select("lp");
  });

  document.querySelectorAll('[data-viz="branch-bound"]').forEach(function (root) {
    var data = parseData(root, ".bnb-data");
    var enhanced = root.querySelector(".bnb-enhanced");
    var fallback = root.querySelector(".bnb-fallback");
    var certificate = root.querySelector("[data-bnb-certificate]");
    var buttons = Array.from(root.querySelectorAll("[data-bnb-step]"));
    if (!data || !enhanced || !fallback || !certificate || !buttons.length) return;

    function numeric(value) {
      if (value === null) return null;
      if (String(value).indexOf("/") === -1) return Number(value);
      var bits = String(value).split("/");
      return Number(bits[0]) / Number(bits[1]);
    }

    function select(index) {
      var snapshot = data.snapshots[index];
      if (!snapshot) return;
      buttons.forEach(function (button) {
        button.setAttribute("aria-pressed", String(Number(button.dataset.bnbStep) === index));
      });
      var lower = numeric(snapshot.lower);
      var upper = numeric(snapshot.upper);
      var heading = lower === null ? "No incumbent yet" : snapshot.lower + " ≤ z* ≤ " + snapshot.upper;
      var caption = lower === null ? "Before an integer solution is found" : "Certified maximisation interval";
      var chartMinimum = data.scale_minimum;
      var chartMaximum = data.scale_maximum;
      var chartSpan = chartMaximum - chartMinimum;
      var width = lower === null ? 100 : Math.max(0, Math.min(100, (upper - lower) / chartSpan * 100));
      var left = lower === null ? 0 : Math.max(0, Math.min(100, (lower - chartMinimum) / chartSpan * 100));
      var boundDetails = Object.keys(snapshot.open_bounds).map(function (name) {
        return name + " ≤ " + snapshot.open_bounds[name];
      });
      var open = boundDetails.length ? "Open bounds: " + boundDetails.join(", ") : "No open nodes remain";
      certificate.innerHTML = "<small>" + caption + "</small><strong>" + heading
        + "</strong><div class=\"bnb-interval\" aria-hidden=\"true\"><i style=\"--bnb-left:"
        + left + "%;--bnb-width:" + width + "%\"></i></div><p>" + snapshot.event
        + "</p><span>" + open + " · global upper bound U = " + snapshot.upper + "</span>";
    }

    buttons.forEach(function (button) {
      button.addEventListener("click", function () { select(Number(button.dataset.bnbStep)); });
    });
    // Keep the complete branch tree visible; the controls add a live
    // certificate timeline below it rather than replacing the illustration.
    enhanced.hidden = false;
    select(0);
  });
}());
