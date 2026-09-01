import Darwin
import Foundation

enum BackendStatus: Equatable {
    case starting
    case ready
    case failed(String)
}

@MainActor
final class BackendRuntime: ObservableObject {
    @Published private(set) var status: BackendStatus = .starting

    static let baseURL = URL(string: "http://127.0.0.1:8765")!
    // /api/health/ready (not /api/health) so a database that isn't up yet is a
    // clear 503 instead of a 200-with-degraded-body that a status-code check
    // can't tell apart from "fully ready".
    private static let readyURL = baseURL.appendingPathComponent("api/health/ready")

    private var process: Process?
    private var pollTask: Task<Void, Never>?
    private var isStoppingIntentionally = false

    func start() {
        guard process == nil else { return }

        let executableURL = Bundle.main.resourceURL!
            .appendingPathComponent("backend")
            .appendingPathComponent("db-playground-backend")
        let logURL = Self.logFileURL()

        guard FileManager.default.fileExists(atPath: executableURL.path) else {
            status = .failed("백엔드 실행 파일을 찾을 수 없습니다: \(executableURL.path)")
            return
        }

        FileManager.default.createFile(atPath: logURL.path, contents: nil)
        let logHandle = try? FileHandle(forWritingTo: logURL)

        let process = Process()
        process.executableURL = executableURL
        process.standardOutput = logHandle
        process.standardError = logHandle
        process.terminationHandler = { [weak self] proc in
            Task { @MainActor in
                guard let self, !self.isStoppingIntentionally else { return }
                // Reachable from .starting (never came up) or .ready (crashed
                // later) alike -- either way this is unexpected, not a normal
                // app-quit shutdown, so the UI must not stay on a stale "ready"
                // webview pointed at a backend that no longer exists. The crashed
                // process's own postgres/mongod children never got the graceful
                // shutdown its (never-reached) `finally` block would have given
                // them, so clean up its whole process group as a safety net.
                Self.killProcessGroup(of: proc.processIdentifier)
                self.status = .failed(
                    "백엔드 프로세스가 예기치 않게 종료되었습니다 (코드 \(proc.terminationStatus)). "
                        + "로그: \(logURL.path)"
                )
            }
        }

        do {
            try process.run()
            self.process = process
        } catch {
            status = .failed("백엔드를 시작하지 못했습니다: \(error.localizedDescription)")
            return
        }

        pollTask = Task { await self.pollHealth() }
    }

    private func pollHealth() async {
        let deadline = Date().addingTimeInterval(45)
        while Date() < deadline {
            if Task.isCancelled { return }
            if let (_, response) = try? await URLSession.shared.data(from: Self.readyURL),
                let http = response as? HTTPURLResponse, http.statusCode == 200
            {
                status = .ready
                return
            }
            try? await Task.sleep(nanoseconds: 500_000_000)
        }
        if case .starting = status {
            status = .failed("데이터베이스 서버가 제한 시간 안에 준비되지 않았습니다.")
        }
    }

    func stop() {
        isStoppingIntentionally = true
        pollTask?.cancel()
        guard let process, process.isRunning else { return }
        process.terminate()
        process.waitUntilExit()
    }

    /// `app.desktop.runtime.main()` calls `os.setpgrp()`, so this pid is also
    /// its process group id -- postgres/mongod inherit that group, and it stays
    /// addressable via kill(-pgid, ...) even after the leader itself has died.
    /// SIGTERM first for a clean shutdown attempt, SIGKILL shortly after for
    /// whatever ignores it.
    private static func killProcessGroup(of pid: pid_t) {
        Darwin.kill(-pid, SIGTERM)
        DispatchQueue.global().asyncAfter(deadline: .now() + 2) {
            Darwin.kill(-pid, SIGKILL)
        }
    }

    private static func logFileURL() -> URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("DBPlayground/logs", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("launcher.log")
    }
}
