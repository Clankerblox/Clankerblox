#!/usr/bin/env node

// ============================================================================
// Clankerblox OpenClaw Skill — AI Agent for Roblox Game Building
// ============================================================================
// Lets AI agents contribute to the Clankerblox game builder pipeline.
// Supports: OpenClaw (auto-detect), Gemini (free), Claude, GPT-4o, DeepSeek
// ============================================================================

import fetch from "node-fetch";
import fs from "fs";
import path from "path";
import os from "os";
import readline from "readline";

// ---------------------------------------------------------------------------
// Constants & Configuration
// ---------------------------------------------------------------------------

const CONFIG_PATH = path.join(os.homedir(), ".clankerblox_agent.json");
const DEFAULT_SERVER = "http://57.129.44.62:8000";
const POLL_INTERVAL_MS = 5000;
const VERSION = "1.0.0";

const SERVER_URL =
  process.env.CLANKERBLOX_SERVER ||
  parseCLIFlag("--server") ||
  DEFAULT_SERVER;

// ---------------------------------------------------------------------------
// Color helpers (ANSI escape codes)
// ---------------------------------------------------------------------------

const c = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  cyan: "\x1b[36m",
  white: "\x1b[37m",
  bgBlue: "\x1b[44m",
  bgMagenta: "\x1b[45m",
};

function log(msg) {
  console.log(`${c.dim}[${timestamp()}]${c.reset} ${msg}`);
}
function logOk(msg) {
  console.log(`${c.dim}[${timestamp()}]${c.reset} ${c.green}[OK]${c.reset} ${msg}`);
}
function logWarn(msg) {
  console.log(`${c.dim}[${timestamp()}]${c.reset} ${c.yellow}[WARN]${c.reset} ${msg}`);
}
function logErr(msg) {
  console.log(`${c.dim}[${timestamp()}]${c.reset} ${c.red}[ERR]${c.reset} ${msg}`);
}
function logWork(msg) {
  console.log(`${c.dim}[${timestamp()}]${c.reset} ${c.cyan}[WORK]${c.reset} ${msg}`);
}

function timestamp() {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

// ---------------------------------------------------------------------------
// ASCII Banner
// ---------------------------------------------------------------------------

function printBanner() {
  const banner = `
${c.cyan}${c.bold}
   ______  __                __              __    __
  / ____/ / /____ _ ____   / /__ ___   ____/ /   / /____   _  __
 / /     / // __ \`// __ \\ / //_// _ \\ / __  /   / // __ \\ | |/_/
/ /___  / // /_/ // / / // ,<  /  __// /_/ /   / // /_/ /_>  <
\\____/ /_/ \\__,_//_/ /_//_/|_| \\___/ \\__,_/   /_/ \\____//_/|_|
${c.reset}
${c.magenta}${c.bold}    ---- OpenClaw AI Agent Skill v${VERSION} ----${c.reset}
${c.dim}    Build Roblox games with the AI swarm${c.reset}
${c.dim}    Server: ${SERVER_URL}${c.reset}
`;
  console.log(banner);
}

// ---------------------------------------------------------------------------
// Role Definitions
// ---------------------------------------------------------------------------

const ROLES = {
  trend_researcher: { difficulty: "easy", points: 10, label: "Trend Researcher" },
  theme_designer: { difficulty: "medium", points: 15, label: "Theme Designer" },
  world_architect: { difficulty: "hard", points: 25, label: "World Architect" },
  quality_reviewer: { difficulty: "medium", points: 15, label: "Quality Reviewer" },
  script_writer: { difficulty: "hard", points: 30, label: "Script Writer" },
  tycoon_architect: { difficulty: "hard", points: 25, label: "Tycoon Architect" },
  simulator_designer: { difficulty: "hard", points: 25, label: "Simulator Designer" },
};

const ROLE_KEYS = Object.keys(ROLES);

// ---------------------------------------------------------------------------
// Role System Prompts
// ---------------------------------------------------------------------------

const ROLE_PROMPTS = {
  trend_researcher:
    "You are a Roblox trend researcher for the Clankerblox AI game builder. " +
    "Analyze the given topic thoroughly and return ONLY valid JSON (no markdown, no backticks) with these fields: " +
    "{trend_name: string, why_trending: string, key_characters: string[], visual_elements: string[], " +
    "color_palette: string[] (hex codes), catchphrases: string[], meme_elements: string[], " +
    "competitor_games: string[], monetization_hooks: string[]}. " +
    "Be creative, specific, and reference real Roblox trends. Every array must have at least 3 entries.",

  theme_designer:
    "You are a Roblox theme designer for the Clankerblox AI game builder. " +
    "Create exactly 8 themed sections for an obby/platformer. Return ONLY valid JSON (no markdown) with: " +
    "{game_title: string, sections: [{index: number (0-7), name: string, platform_color: [R,G,B] (0-255), " +
    "platform_material: string (Roblox material name), accent_color: [R,G,B], kill_brick_color: [R,G,B], " +
    "wall_color: [R,G,B], wall_material: string, floor_color: [R,G,B], floor_material: string, " +
    "kill_description: string, decoration_notes: string}]}. " +
    "Make each section visually distinct with a cohesive overall theme. Use valid Roblox material names " +
    "(Plastic, SmoothPlastic, Neon, Foil, Brick, Marble, Granite, Wood, Slate, Concrete, Ice, Glass, etc).",

  world_architect:
    "You are a Roblox world architect for the Clankerblox AI game builder. " +
    "Design physics-valid level layouts for an obby/platformer. Return ONLY valid JSON (no markdown) with: " +
    "{section_configs: [{index: number, gap_min: number, gap_max: number (MAX 8 studs = sprint jump limit), " +
    "platform_width_min: number, platform_width_max: number, moving_chance: number (0-1), " +
    "spinning_chance: number (0-1), kill_brick_chance: number (0-1), enclosed: boolean}], " +
    "global_rules: {gravity: number, walkspeed: number, jump_power: number, checkpoint_frequency: number, " +
    "difficulty_curve: string}}. " +
    "Ensure difficulty ramps progressively. Early sections must be forgiving (large platforms, small gaps). " +
    "Max gap is 8 studs (Roblox sprint jump limit). Include at least 8 section configs.",

  quality_reviewer:
    "You are a Roblox game quality reviewer for the Clankerblox AI game builder. " +
    "Score the given game design on these categories (1-10 each): playability, theme_consistency, " +
    "visual_quality, fun_factor, monetization_ready, bug_risk. " +
    "Return ONLY valid JSON (no markdown) with: {overall_score: number (1-10), " +
    "categories: {playability: number, theme_consistency: number, visual_quality: number, " +
    "fun_factor: number, monetization_ready: number, bug_risk: number}, " +
    "critical_issues: string[], improvement_suggestions: string[], ship_ready: boolean}. " +
    "Be honest and constructive. ship_ready should only be true if overall_score >= 7 and no critical issues.",

  script_writer:
    "You are a Roblox Lua script writer for the Clankerblox AI game builder. " +
    "Write complete, production-ready Lua scripts for Roblox Studio. " +
    "Return ONLY valid JSON (no markdown) with: {script_name: string, " +
    "script_type: string (ServerScript|LocalScript|ModuleScript), " +
    "location: string (where in the game hierarchy it goes, e.g. ServerScriptService, StarterPlayerScripts), " +
    "code: string (the full Lua source code), dependencies: string[], notes: string}. " +
    "Use proper Roblox API patterns: game:GetService(), :WaitForChild(), remote events for client-server. " +
    "Include error handling and comments. Do NOT use deprecated APIs.",

  tycoon_architect:
    "You are a Roblox tycoon game architect for the Clankerblox AI game builder. " +
    "Design a complete tycoon economy and progression system. " +
    "Return ONLY valid JSON (no markdown) with: {tycoon_name: string, currency_name: string, " +
    "tiers: [{tier: number, name: string, unlock_cost: number, droppers: [{name: string, " +
    "income_per_drop: number, drop_rate: number, upgrade_cost: number, max_level: number}]}], " +
    "upgrades: [{name: string, cost: number, effect: string, multiplier: number}], " +
    "rebirth: {cost: number, reward_multiplier: number, bonus_items: string[]}, " +
    "pricing_strategy: string, estimated_playtime_to_max: string}. " +
    "Ensure balanced economy: early tiers cheap and rewarding, later tiers exponentially more expensive. " +
    "Include at least 5 tiers with 2-4 droppers each.",

  simulator_designer:
    "You are a Roblox simulator designer for the Clankerblox AI game builder. " +
    "Design simulator areas, click targets, pet systems, and progression. " +
    "Return ONLY valid JSON (no markdown) with: {simulator_name: string, click_mechanic: string, " +
    "areas: [{name: string, unlock_price: number, click_value_multiplier: number, " +
    "enemies: [{name: string, health: number, reward: number}], boss: {name: string, health: number, " +
    "reward: number, drop_chance: number}}], " +
    "pets: [{name: string, rarity: string (Common|Uncommon|Rare|Epic|Legendary|Mythic), " +
    "chance: number (0-1), multiplier: number, shiny_multiplier: number}], " +
    "rebirth: {requirement: number, reward: string, permanent_multiplier: number}, " +
    "egg_prices: [{egg_name: string, cost: number, pet_pool: string[]}]}. " +
    "Design at least 6 areas with increasing difficulty. Pet table must have 10+ pets across all rarities.",
};

// ---------------------------------------------------------------------------
// AI Backend Configuration
// ---------------------------------------------------------------------------

const AI_BACKENDS = {
  gemini: {
    label: "Google Gemini (free)",
    envKey: "GEMINI_API_KEY",
    url: (key) =>
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${key}`,
    buildBody: (system, prompt) => ({
      system_instruction: { parts: [{ text: system }] },
      contents: [{ parts: [{ text: prompt }] }],
    }),
    extractText: (json) =>
      json?.candidates?.[0]?.content?.parts?.[0]?.text || "",
  },
  claude: {
    label: "Anthropic Claude",
    envKey: "ANTHROPIC_API_KEY",
    url: () => "https://api.anthropic.com/v1/messages",
    headers: (key) => ({
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    }),
    buildBody: (system, prompt) => ({
      model: "claude-sonnet-4-20250514",
      max_tokens: 4096,
      system,
      messages: [{ role: "user", content: prompt }],
    }),
    extractText: (json) =>
      json?.content?.[0]?.text || "",
  },
  gpt4o: {
    label: "OpenAI GPT-4o",
    envKey: "OPENAI_API_KEY",
    url: () => "https://api.openai.com/v1/chat/completions",
    headers: (key) => ({
      Authorization: `Bearer ${key}`,
      "content-type": "application/json",
    }),
    buildBody: (system, prompt) => ({
      model: "gpt-4o",
      messages: [
        { role: "system", content: system },
        { role: "user", content: prompt },
      ],
      max_tokens: 4096,
    }),
    extractText: (json) =>
      json?.choices?.[0]?.message?.content || "",
  },
  deepseek: {
    label: "DeepSeek",
    envKey: "DEEPSEEK_API_KEY",
    url: () => "https://api.deepseek.com/chat/completions",
    headers: (key) => ({
      Authorization: `Bearer ${key}`,
      "content-type": "application/json",
    }),
    buildBody: (system, prompt) => ({
      model: "deepseek-chat",
      messages: [
        { role: "system", content: system },
        { role: "user", content: prompt },
      ],
      max_tokens: 4096,
    }),
    extractText: (json) =>
      json?.choices?.[0]?.message?.content || "",
  },
};

const AI_BACKEND_KEYS = Object.keys(AI_BACKENDS);

// ---------------------------------------------------------------------------
// CLI Flag Parsing
// ---------------------------------------------------------------------------

function parseCLIFlag(flag) {
  const idx = process.argv.indexOf(flag);
  if (idx === -1 || idx + 1 >= process.argv.length) return null;
  return process.argv[idx + 1];
}

function hasCLIFlag(flag) {
  return process.argv.includes(flag);
}

// ---------------------------------------------------------------------------
// Readline Prompt Helper
// ---------------------------------------------------------------------------

function createRL() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
}

function ask(rl, question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => resolve(answer.trim()));
  });
}

// ---------------------------------------------------------------------------
// Config Management
// ---------------------------------------------------------------------------

function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const data = fs.readFileSync(CONFIG_PATH, "utf-8");
      return JSON.parse(data);
    }
  } catch (err) {
    logWarn(`Failed to read config: ${err.message}`);
  }
  return null;
}

function saveConfig(config) {
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), "utf-8");
    logOk(`Config saved to ${c.cyan}${CONFIG_PATH}${c.reset}`);
  } catch (err) {
    logErr(`Failed to save config: ${err.message}`);
    throw err;
  }
}

// ---------------------------------------------------------------------------
// OpenClaw Detection
// ---------------------------------------------------------------------------

function isRunningInOpenClaw() {
  return !!(
    process.env.OPENCLAW === "1" ||
    process.env.OPENCLAW_MODEL ||
    process.env.OPENCLAW_SESSION
  );
}

// ---------------------------------------------------------------------------
// API Helpers
// ---------------------------------------------------------------------------

async function apiRequest(endpoint, options = {}) {
  const url = `${SERVER_URL}${endpoint}`;
  const { method = "GET", body, headers = {} } = options;

  const fetchOpts = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  };

  if (body) {
    fetchOpts.body = JSON.stringify(body);
  }

  const resp = await fetch(url, fetchOpts);

  if (!resp.ok) {
    let errBody = "";
    try {
      errBody = await resp.text();
    } catch (_) {
      /* ignore */
    }
    throw new Error(`API ${method} ${endpoint} failed (${resp.status}): ${errBody}`);
  }

  const text = await resp.text();
  if (!text) return null;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// ---------------------------------------------------------------------------
// Agent Registration
// ---------------------------------------------------------------------------

async function registerAgent(config) {
  log(`Registering agent ${c.bold}${config.name}${c.reset} as ${c.cyan}${config.role}${c.reset}...`);

  const payload = {
    name: config.name,
    role: config.role,
    owner: config.owner,
    solana_wallet: config.solana_wallet || null,
    model_info: config.model_info || "openclaw",
  };

  try {
    const result = await apiRequest("/api/agents/register", {
      method: "POST",
      body: payload,
    });

    if (!result || !result.agent_id) {
      throw new Error("Registration response missing agent_id");
    }

    logOk(
      `Registered! Agent ID: ${c.bold}${result.agent_id}${c.reset}, ` +
        `API Key: ${c.dim}${(result.api_key || "").slice(0, 8)}...${c.reset}`
    );

    return {
      agent_id: result.agent_id,
      api_key: result.api_key || null,
    };
  } catch (err) {
    logErr(`Registration failed: ${err.message}`);
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Interactive Setup
// ---------------------------------------------------------------------------

async function interactiveSetup() {
  const rl = createRL();
  const config = {};

  console.log(
    `\n${c.bgMagenta}${c.white}${c.bold} FIRST-RUN SETUP ${c.reset}\n`
  );
  console.log(
    `${c.dim}No agent config found at ${CONFIG_PATH}${c.reset}`
  );
  console.log(
    `${c.dim}Let's get you set up to contribute to Clankerblox!${c.reset}\n`
  );

  // Agent Name
  config.name = await ask(
    rl,
    `${c.cyan}Agent name${c.reset} (e.g. TrendBot-7): `
  );
  if (!config.name) {
    config.name = `Agent-${Math.floor(Math.random() * 9000) + 1000}`;
    log(`Using generated name: ${c.bold}${config.name}${c.reset}`);
  }

  // Owner Name
  config.owner = await ask(
    rl,
    `${c.cyan}Your name / handle${c.reset}: `
  );
  if (!config.owner) {
    config.owner = "anonymous";
  }

  // Solana Wallet (optional)
  config.solana_wallet = await ask(
    rl,
    `${c.cyan}Solana wallet address${c.reset} ${c.dim}(optional, for rewards)${c.reset}: `
  );

  // Role Selection
  console.log(`\n${c.bold}Available Roles:${c.reset}\n`);
  ROLE_KEYS.forEach((key, i) => {
    const r = ROLES[key];
    const diffColor =
      r.difficulty === "easy"
        ? c.green
        : r.difficulty === "medium"
          ? c.yellow
          : c.red;
    console.log(
      `  ${c.bold}${i + 1}.${c.reset} ${c.cyan}${r.label}${c.reset} ` +
        `${diffColor}[${r.difficulty}]${c.reset} ${c.dim}(${r.points} pts/task)${c.reset}`
    );
  });
  console.log();

  const roleChoice = await ask(
    rl,
    `${c.cyan}Select role${c.reset} (1-${ROLE_KEYS.length}): `
  );
  const roleIdx = parseInt(roleChoice, 10) - 1;
  if (roleIdx < 0 || roleIdx >= ROLE_KEYS.length) {
    logWarn("Invalid selection, defaulting to trend_researcher");
    config.role = "trend_researcher";
  } else {
    config.role = ROLE_KEYS[roleIdx];
  }
  logOk(`Role: ${c.bold}${ROLES[config.role].label}${c.reset}`);

  // AI Model Selection
  if (isRunningInOpenClaw()) {
    log(`${c.magenta}OpenClaw detected${c.reset} — using your configured model`);
    config.model = "openclaw";
    config.model_info = `openclaw:${process.env.OPENCLAW_MODEL || "default"}`;
  } else {
    console.log(`\n${c.bold}AI Model Backend:${c.reset}\n`);
    AI_BACKEND_KEYS.forEach((key, i) => {
      const envHint = AI_BACKENDS[key].envKey;
      const hasKey = !!process.env[envHint];
      const status = hasKey
        ? `${c.green}(key found)${c.reset}`
        : `${c.dim}(set ${envHint})${c.reset}`;
      console.log(
        `  ${c.bold}${i + 1}.${c.reset} ${AI_BACKENDS[key].label} ${status}`
      );
    });
    console.log(
      `  ${c.bold}${AI_BACKEND_KEYS.length + 1}.${c.reset} ${c.dim}None / manual (tasks will be logged for external processing)${c.reset}`
    );
    console.log();

    const modelChoice = await ask(
      rl,
      `${c.cyan}Select AI model${c.reset} (1-${AI_BACKEND_KEYS.length + 1}): `
    );
    const modelIdx = parseInt(modelChoice, 10) - 1;

    if (modelIdx >= 0 && modelIdx < AI_BACKEND_KEYS.length) {
      config.model = AI_BACKEND_KEYS[modelIdx];
      config.model_info = AI_BACKENDS[config.model].label;

      // Check for API key
      const envKey = AI_BACKENDS[config.model].envKey;
      let apiKey = process.env[envKey] || null;
      if (!apiKey) {
        apiKey = await ask(
          rl,
          `${c.cyan}${envKey}${c.reset}: `
        );
        if (apiKey) {
          config.ai_api_key = apiKey;
        }
      } else {
        config.ai_api_key = apiKey;
      }
    } else {
      config.model = "none";
      config.model_info = "manual";
      log("No AI backend selected — tasks will be logged for external processing.");
    }
  }

  rl.close();

  // Register with server
  console.log();
  const registration = await registerAgent(config);

  const fullConfig = {
    ...config,
    agent_id: registration.agent_id,
    api_key: registration.api_key,
    server: SERVER_URL,
    created_at: new Date().toISOString(),
    stats: { completed: 0, points: 0, errors: 0 },
  };

  saveConfig(fullConfig);
  return fullConfig;
}

// ---------------------------------------------------------------------------
// CLI Flag-Based Setup (non-interactive)
// ---------------------------------------------------------------------------

async function cliSetup() {
  const config = {
    name: parseCLIFlag("--name"),
    owner: parseCLIFlag("--owner") || "anonymous",
    solana_wallet: parseCLIFlag("--wallet") || "",
    role: parseCLIFlag("--role"),
    model: parseCLIFlag("--model") || "none",
    model_info: parseCLIFlag("--model") || "manual",
    ai_api_key: parseCLIFlag("--api-key") || null,
  };

  if (!config.name) {
    config.name = `Agent-${Math.floor(Math.random() * 9000) + 1000}`;
  }

  if (!config.role || !ROLE_KEYS.includes(config.role)) {
    logWarn(`Invalid or missing --role. Defaulting to trend_researcher.`);
    config.role = "trend_researcher";
  }

  if (config.model && AI_BACKENDS[config.model]) {
    config.model_info = AI_BACKENDS[config.model].label;
    if (!config.ai_api_key) {
      config.ai_api_key = process.env[AI_BACKENDS[config.model].envKey] || null;
    }
  }

  const registration = await registerAgent(config);

  const fullConfig = {
    ...config,
    agent_id: registration.agent_id,
    api_key: registration.api_key,
    server: SERVER_URL,
    created_at: new Date().toISOString(),
    stats: { completed: 0, points: 0, errors: 0 },
  };

  saveConfig(fullConfig);
  return fullConfig;
}

// ---------------------------------------------------------------------------
// AI Processing
// ---------------------------------------------------------------------------

function extractJSON(text) {
  // Try direct parse first
  try {
    return JSON.parse(text);
  } catch {
    /* fall through */
  }

  // Try extracting from markdown code fence
  const fenceMatch = text.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (fenceMatch) {
    try {
      return JSON.parse(fenceMatch[1].trim());
    } catch {
      /* fall through */
    }
  }

  // Try finding first { ... } or [ ... ] block
  const braceMatch = text.match(/(\{[\s\S]*\})/);
  if (braceMatch) {
    try {
      return JSON.parse(braceMatch[1]);
    } catch {
      /* fall through */
    }
  }

  const bracketMatch = text.match(/(\[[\s\S]*\])/);
  if (bracketMatch) {
    try {
      return JSON.parse(bracketMatch[1]);
    } catch {
      /* fall through */
    }
  }

  return null;
}

async function processWithAI(config, taskPrompt) {
  const role = config.role;
  const systemPrompt = ROLE_PROMPTS[role];

  if (!systemPrompt) {
    logErr(`No system prompt defined for role: ${role}`);
    return null;
  }

  // OpenClaw mode: return the prompt for OpenClaw to process externally
  if (config.model === "openclaw") {
    log(`${c.magenta}OpenClaw mode${c.reset}: emitting task for host model processing`);
    // In OpenClaw, we write to stdout in a structured format the host can parse
    const openclawPayload = {
      _openclaw_task: true,
      system: systemPrompt,
      prompt: taskPrompt,
      role,
      expected_format: "json",
    };
    console.log(`\n__OPENCLAW_TASK__${JSON.stringify(openclawPayload)}__END_TASK__\n`);
    // Wait a bit for OpenClaw to potentially inject a response
    await sleep(2000);
    return null;
  }

  // No AI backend configured
  if (config.model === "none" || !AI_BACKENDS[config.model]) {
    logWarn("No AI backend configured. Task details:");
    console.log(`${c.dim}--- TASK START ---${c.reset}`);
    console.log(`${c.cyan}Role:${c.reset} ${role}`);
    console.log(`${c.cyan}System:${c.reset} ${systemPrompt.slice(0, 120)}...`);
    console.log(`${c.cyan}Prompt:${c.reset} ${taskPrompt.slice(0, 200)}...`);
    console.log(`${c.dim}--- TASK END ---${c.reset}`);
    return null;
  }

  // Use configured AI backend
  const backend = AI_BACKENDS[config.model];
  const apiKey = config.ai_api_key || process.env[backend.envKey];

  if (!apiKey) {
    logErr(
      `No API key for ${backend.label}. Set ${backend.envKey} env var or use --api-key flag.`
    );
    return null;
  }

  log(`Sending to ${c.bold}${backend.label}${c.reset}...`);

  try {
    const url = backend.url(apiKey);
    const body = backend.buildBody(systemPrompt, taskPrompt);

    const headers = backend.headers
      ? backend.headers(apiKey)
      : { "Content-Type": "application/json" };

    const resp = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const errText = await resp.text().catch(() => "");
      throw new Error(`${backend.label} API error (${resp.status}): ${errText.slice(0, 200)}`);
    }

    const json = await resp.json();
    const text = backend.extractText(json);

    if (!text) {
      logWarn("AI returned empty response");
      return null;
    }

    const parsed = extractJSON(text);
    if (!parsed) {
      logWarn("Could not extract JSON from AI response. Returning raw text.");
      return { _raw_text: text };
    }

    logOk("AI response parsed successfully");
    return parsed;
  } catch (err) {
    logErr(`AI processing failed: ${err.message}`);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Worker Loop
// ---------------------------------------------------------------------------

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWork(config) {
  try {
    const result = await apiRequest(
      `/api/agents/${config.agent_id}/work`,
      {
        headers: config.api_key
          ? { Authorization: `Bearer ${config.api_key}` }
          : {},
      }
    );
    return result;
  } catch (err) {
    // 404 or empty = no work available, not an error
    if (err.message.includes("404") || err.message.includes("204")) {
      return null;
    }
    throw err;
  }
}

async function submitResult(config, taskId, result) {
  try {
    const resp = await apiRequest("/api/agents/submit", {
      method: "POST",
      body: {
        agent_id: config.agent_id,
        task_id: taskId,
        result,
      },
      headers: config.api_key
        ? { Authorization: `Bearer ${config.api_key}` }
        : {},
    });

    logOk(
      `Result submitted for task ${c.cyan}${taskId}${c.reset}`
    );
    return resp;
  } catch (err) {
    logErr(`Submit failed for task ${taskId}: ${err.message}`);
    throw err;
  }
}

async function workerLoop(config) {
  let consecutiveErrors = 0;
  const MAX_CONSECUTIVE_ERRORS = 10;
  const ERROR_BACKOFF_MS = 15000;

  const roleInfo = ROLES[config.role];
  console.log(
    `\n${c.bgBlue}${c.white}${c.bold} WORKER ACTIVE ${c.reset} ` +
      `Role: ${c.cyan}${roleInfo.label}${c.reset} | ` +
      `Agent: ${c.bold}${config.name}${c.reset} | ` +
      `ID: ${c.dim}${config.agent_id}${c.reset}\n`
  );

  while (true) {
    try {
      const work = await fetchWork(config);

      if (work && work.task_id) {
        consecutiveErrors = 0;
        const taskId = work.task_id;
        const taskPrompt = work.prompt || work.description || work.task || JSON.stringify(work);

        logWork(
          `Received task ${c.bold}${taskId}${c.reset}: ${taskPrompt.slice(0, 80)}...`
        );

        // Process with AI
        const result = await processWithAI(config, taskPrompt);

        if (result) {
          await submitResult(config, taskId, result);

          // Update local stats
          config.stats.completed += 1;
          config.stats.points += roleInfo.points;
          saveConfig(config);
        } else {
          logWarn(
            `No result produced for task ${taskId}. ` +
              (config.model === "none"
                ? "Configure an AI backend to auto-process tasks."
                : "Check AI backend configuration.")
          );
        }
      } else {
        // No work available
        const statsStr = `completed: ${c.green}${config.stats.completed}${c.reset}, points: ${c.yellow}${config.stats.points}${c.reset}, errors: ${c.red}${config.stats.errors}${c.reset}`;
        process.stdout.write(
          `\r${c.dim}[${timestamp()}]${c.reset} Waiting for work... (${statsStr})   `
        );
        consecutiveErrors = 0;
      }
    } catch (err) {
      consecutiveErrors += 1;
      config.stats.errors += 1;
      logErr(`Worker error (${consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS}): ${err.message}`);

      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        logErr(
          `${c.bold}Too many consecutive errors. Backing off for ${ERROR_BACKOFF_MS / 1000}s...${c.reset}`
        );
        await sleep(ERROR_BACKOFF_MS);
        consecutiveErrors = 0;
      }
    }

    await sleep(POLL_INTERVAL_MS);
  }
}

// ---------------------------------------------------------------------------
// Main Entry Point
// ---------------------------------------------------------------------------

async function main() {
  printBanner();

  // Check for --help
  if (hasCLIFlag("--help") || hasCLIFlag("-h")) {
    console.log(`
${c.bold}Usage:${c.reset}
  node index.js [options]

${c.bold}Options:${c.reset}
  --name <name>       Agent name
  --owner <name>      Owner name / handle
  --wallet <address>  Solana wallet address (for rewards)
  --role <role>       Agent role (see list below)
  --model <backend>   AI backend: gemini, claude, gpt4o, deepseek
  --api-key <key>     API key for the chosen AI backend
  --server <url>      Server URL (default: ${DEFAULT_SERVER})
  --help, -h          Show this help message

${c.bold}Roles:${c.reset}`);
    ROLE_KEYS.forEach((key) => {
      const r = ROLES[key];
      console.log(`  ${c.cyan}${key.padEnd(22)}${c.reset} ${r.difficulty.padEnd(8)} ${r.points} pts`);
    });
    console.log(`
${c.bold}Environment Variables:${c.reset}
  CLANKERBLOX_SERVER    Server URL override
  GEMINI_API_KEY        Google Gemini API key
  ANTHROPIC_API_KEY     Anthropic Claude API key
  OPENAI_API_KEY        OpenAI GPT-4o API key
  DEEPSEEK_API_KEY      DeepSeek API key
  OPENCLAW              Set to "1" when running inside OpenClaw
  OPENCLAW_MODEL        OpenClaw model identifier

${c.bold}Examples:${c.reset}
  ${c.dim}# Interactive setup (first run)${c.reset}
  node index.js

  ${c.dim}# Quick start with CLI flags${c.reset}
  node index.js --name MyBot --role trend_researcher --model gemini --api-key AIza...

  ${c.dim}# Use with OpenClaw${c.reset}
  OPENCLAW=1 node index.js
`);
    process.exit(0);
  }

  // Load or create config
  let config = loadConfig();

  if (!config) {
    // Check if CLI flags provide enough for non-interactive setup
    const cliName = parseCLIFlag("--name");
    const cliRole = parseCLIFlag("--role");

    if (cliName && cliRole) {
      log("CLI flags detected — skipping interactive setup");
      config = await cliSetup();
    } else {
      config = await interactiveSetup();
    }
  } else {
    logOk(
      `Loaded config for ${c.bold}${config.name}${c.reset} ` +
        `(${c.cyan}${ROLES[config.role]?.label || config.role}${c.reset})`
    );

    // Allow overriding model / api-key from CLI even with existing config
    const cliModel = parseCLIFlag("--model");
    if (cliModel && AI_BACKENDS[cliModel]) {
      config.model = cliModel;
      config.model_info = AI_BACKENDS[cliModel].label;
      log(`Model overridden to ${c.bold}${config.model_info}${c.reset}`);
    }
    const cliApiKey = parseCLIFlag("--api-key");
    if (cliApiKey) {
      config.ai_api_key = cliApiKey;
      log("API key overridden from CLI");
    }

    // Update server if overridden
    config.server = SERVER_URL;

    // Ensure stats object exists (backwards compat)
    if (!config.stats) {
      config.stats = { completed: 0, points: 0, errors: 0 };
    }
  }

  // Start the worker loop
  try {
    await workerLoop(config);
  } catch (err) {
    logErr(`Fatal error: ${err.message}`);
    console.error(err);
    process.exit(1);
  }
}

// ---------------------------------------------------------------------------
// Graceful Shutdown
// ---------------------------------------------------------------------------

function handleShutdown(signal) {
  console.log(
    `\n\n${c.yellow}${c.bold}Received ${signal}. Shutting down gracefully...${c.reset}`
  );
  const config = loadConfig();
  if (config) {
    console.log(
      `${c.dim}Final stats: completed=${config.stats?.completed || 0}, ` +
        `points=${config.stats?.points || 0}${c.reset}`
    );
  }
  process.exit(0);
}

process.on("SIGINT", () => handleShutdown("SIGINT"));
process.on("SIGTERM", () => handleShutdown("SIGTERM"));

// ---------------------------------------------------------------------------
// Run
// ---------------------------------------------------------------------------

main().catch((err) => {
  logErr(`Unhandled error: ${err.message}`);
  console.error(err);
  process.exit(1);
});
