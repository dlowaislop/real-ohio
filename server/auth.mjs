// Shared user store for Real Ohio admin.
// Users live in data/users.json (gitignored, never committed).
// Passwords are stored only as scrypt hashes: "scrypt:<salt-hex>:<hash-hex>".
// Both the CLI (scripts/users.mjs) and the admin server (server.mjs) use this.
import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const USERS_PATH = path.join(ROOT, "data", "users.json");

export function loadUsers() {
  try {
    return JSON.parse(fs.readFileSync(USERS_PATH, "utf8"));
  } catch {
    return {};
  }
}

export function saveUsers(users) {
  fs.mkdirSync(path.dirname(USERS_PATH), { recursive: true });
  fs.writeFileSync(USERS_PATH, JSON.stringify(users, null, 2) + "\n", { mode: 0o600 });
}

export function validateUsername(username) {
  if (!/^[a-z0-9._-]{3,32}$/.test(username || "")) {
    throw new Error('Username must be 3-32 chars: lowercase letters, digits, ".", "_", "-".');
  }
}

export function validatePassword(password) {
  if (!password || password.length < 8) {
    throw new Error("Password must be at least 8 characters.");
  }
}

export function hashPassword(password) {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64).toString("hex");
  return `scrypt:${salt}:${hash}`;
}

export function verifyPassword(password, stored) {
  try {
    const [, salt, hashHex] = stored.split(":");
    const hash = Buffer.from(hashHex, "hex");
    const attempt = scryptSync(password, salt, 64);
    return attempt.length === hash.length && timingSafeEqual(attempt, hash);
  } catch {
    return false;
  }
}

export function createUser(username, password) {
  validateUsername(username);
  validatePassword(password);
  const users = loadUsers();
  if (users[username]) throw new Error(`User "${username}" already exists. Use update to change the password.`);
  const now = new Date().toISOString();
  users[username] = { hash: hashPassword(password), created_at: now, updated_at: now };
  saveUsers(users);
  return username;
}

export function updateUser(username, password) {
  validateUsername(username);
  validatePassword(password);
  const users = loadUsers();
  if (!users[username]) throw new Error(`No such user "${username}". Use create first.`);
  users[username].hash = hashPassword(password);
  users[username].updated_at = new Date().toISOString();
  saveUsers(users);
  return username;
}

export function deleteUser(username) {
  const users = loadUsers();
  if (!users[username]) throw new Error(`No such user "${username}".`);
  delete users[username];
  saveUsers(users);
  return username;
}

export function listUsers() {
  const users = loadUsers();
  return Object.keys(users)
    .sort()
    .map((u) => ({ username: u, created_at: users[u].created_at, updated_at: users[u].updated_at }));
}

export function checkLogin(username, password) {
  const users = loadUsers();
  const entry = users[username];
  if (!entry) return false;
  return verifyPassword(password, entry.hash);
}
