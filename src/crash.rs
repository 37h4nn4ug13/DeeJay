use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

use chrono::Utc;

/// Install a panic hook that writes crash information to disk.
pub fn install_panic_hook<P: AsRef<Path>>(log_path: P, version: &str) {
    let path = log_path.as_ref().to_path_buf();
    let version = version.to_owned();

    std::panic::set_hook(Box::new(move |panic_info| {
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        let mut file = match OpenOptions::new()
            .create(true)
            .append(true)
            .open(&path)
        {
            Ok(file) => file,
            Err(_) => return,
        };

        let timestamp = Utc::now().to_rfc3339();
        let _ = writeln!(file, "\n=== crash at {} (version {}) ===", timestamp, version);
        if let Some(location) = panic_info.location() {
            let _ = writeln!(file, "location: {}:{}", location.file(), location.line());
        }
        if let Some(s) = panic_info.payload().downcast_ref::<&str>() {
            let _ = writeln!(file, "message: {}", s);
        } else if let Some(s) = panic_info.payload().downcast_ref::<String>() {
            let _ = writeln!(file, "message: {}", s);
        }
    }));
}

#[cfg(test)]
mod tests {
    use super::install_panic_hook;
    use std::panic;
    use tempfile::tempdir;

    #[test]
    fn writes_crash_logs() {
        let dir = tempdir().unwrap();
        let log_path = dir.path().join("crash.log");
        install_panic_hook(&log_path, "0.0.0-test");

        let result = panic::catch_unwind(|| panic!("boom"));
        assert!(result.is_err());

        let contents = std::fs::read_to_string(&log_path).unwrap();
        assert!(contents.contains("boom"));
        assert!(contents.contains("version"));
    }
}
