#!/usr/bin/env node

import http from "node:http";

const key = process.argv[2] || "events";
const endpointMap = {
  events: "/api/life_events",
  schedules: "/api/scheduled_events",
  profile: "/api/user_profile",
};

if (!endpointMap[key]) {
  console.error(`Unknown target: ${key}. Use one of: events, schedules, profile`);
  process.exit(1);
}

const endpoint = endpointMap[key];

http.get(
  {
    hostname: "localhost",
    port: 5000,
    path: endpoint,
    timeout: 10000,
  },
  (res) => {
    let body = "";
    res.setEncoding("utf8");

    res.on("data", (chunk) => {
      body += chunk;
    });

    res.on("end", () => {
      try {
        const data = JSON.parse(body || "{}");
        console.log(JSON.stringify(data, null, 2));
      } catch (err) {
        console.error("Invalid JSON response:");
        console.error(body);
        process.exit(1);
      }
    });
  }
).on("error", (err) => {
  console.error(`Request failed: ${err.message}`);
  process.exit(1);
});
