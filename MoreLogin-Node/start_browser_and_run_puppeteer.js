const puppeteer = require("puppeteer");
const axios = require("axios");

async function debugPort(profileId) {
  const url = `http://localhost:40000/api/env/start`;
  const response = await axios.post(url, { envId: profileId });
  if (response.data.code === 0) {
    return response.data.data.debugPort;
  }
  return -1;
}

(async function run() {
  const port = await debugPort("1907751741233373184");
  if (port <= 0) {
    console.log("Failed to start the environment");
    return;
  }

  const browserURL = `http://127.0.0.1:${port}`;
  const browser = await puppeteer.connect({ browserURL });
  const page = await browser.newPage();
  await page.goto("https://google.com");
})();