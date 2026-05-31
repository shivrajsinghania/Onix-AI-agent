self.addEventListener("install", (event) => {
  console.log("Service Worker Installed");
});

self.addEventListener("activated", (event) => {
  console.log("Service Worker Activated");
});

self.addEventListener("fetch", (event) => {
  // Let requests pass through normally
});
