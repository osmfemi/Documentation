import { spawn } from "node:child_process";
import { join } from "node:path";

const executable = (name) =>
  join(process.cwd(), "node_modules", ".bin", `${name}${process.platform === "win32" ? ".cmd" : ""}`);

const processes = [
  spawn(executable("velite"), ["dev"], { stdio: "inherit" }),
  spawn(executable("next"), ["dev"], {
    stdio: "inherit",
    env: { ...process.env, NEXT_DIST_DIR: ".next-dev" },
  }),
];

let stopping = false;

function stop(signal, exitCode) {
  if (stopping) return;
  stopping = true;

  for (const child of processes) {
    if (child.exitCode === null) child.kill(signal);
  }

  Promise.all(
    processes.map((child) =>
      child.exitCode === null
        ? new Promise((resolve) => child.once("exit", resolve))
        : Promise.resolve()
    )
  ).then(() => process.exit(exitCode));
}

for (const child of processes) {
  child.once("error", (error) => {
    console.error(error);
    stop("SIGTERM", 1);
  });
  child.once("exit", (code, signal) => {
    if (!stopping) stop("SIGTERM", signal ? 1 : (code ?? 0));
  });
}

process.once("SIGINT", () => stop("SIGINT", 130));
process.once("SIGTERM", () => stop("SIGTERM", 143));
