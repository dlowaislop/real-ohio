#!/usr/bin/env bun
// Real Ohio admin user manager.
// Usage:
//   bun scripts/users.mjs create <username> [--password <pw>]
//   bun scripts/users.mjs update <username> [--password <pw>]
//   bun scripts/users.mjs delete <username>
//   bun scripts/users.mjs list
// Without --password, it prompts (input masked with *).
// Users are stored hashed (scrypt) in data/users.json — never committed.
// Only CLI-created users can log in to /masthead; there is no public signup.
import readline from "node:readline";
import { createUser, deleteUser, listUsers, updateUser } from "../server/auth.mjs";

function arg(name) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

function promptPassword(label) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    const stdin = process.stdin;
    // Mask typed characters when running on a TTY.
    let masked = "";
    const onData = (ch) => {
      const s = ch.toString("utf8");
      if (s === "\r" || s === "\n") return;
      if (s === "\u0003") process.exit(130); // Ctrl-C
      masked += s;
      readline.clearLine(process.stdout, 0);
      readline.cursorTo(process.stdout, 0);
      process.stdout.write(`${label}${"*".repeat(masked.length)}`);
    };
    if (stdin.isTTY) {
      stdin.setRawMode(true);
      stdin.on("data", onData);
    }
    rl.question(label, (answer) => {
      if (stdin.isTTY) {
        stdin.setRawMode(false);
        stdin.removeListener("data", onData);
      }
      process.stdout.write("\n");
      rl.close();
      resolve(answer || masked);
    });
  });
}

const [cmd, username] = process.argv.slice(2);
try {
  if (cmd === "list") {
    const users = listUsers();
    if (!users.length) console.log("No admin users yet. Create one with: bun scripts/users.mjs create <username>");
    else for (const u of users) console.log(`${u.username}\tcreated ${u.created_at}`);
    process.exit(0);
  }
  if (!["create", "update", "delete"].includes(cmd) || !username) {
    console.error("Usage: bun scripts/users.mjs <create|update|delete|list> <username> [--password <pw>]");
    process.exit(2);
  }
  if (cmd === "delete") {
    deleteUser(username);
    console.log(`Deleted user "${username}".`);
    process.exit(0);
  }
  const password = arg("password") || (await promptPassword("Password: "));
  if (cmd === "create") {
    createUser(username, password);
    console.log(`Created user "${username}". They can now log in at /masthead.`);
  } else {
    updateUser(username, password);
    console.log(`Updated password for "${username}".`);
  }
} catch (e) {
  console.error(e.message);
  process.exit(1);
}
