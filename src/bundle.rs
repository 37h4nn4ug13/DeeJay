use std::fs;
use std::path::{Path, PathBuf};

use walkdir::WalkDir;

use crate::settings::Settings;

#[derive(Debug)]
pub struct BundlePlan {
    pub target: String,
    pub dist_dir: PathBuf,
}

impl BundlePlan {
    pub fn new<S: Into<String>>(target: S, dist_dir: impl AsRef<Path>) -> Self {
        Self {
            target: target.into(),
            dist_dir: dist_dir.as_ref().to_path_buf(),
        }
    }

    pub fn output_dir(&self) -> PathBuf {
        self.dist_dir.join(&self.target)
    }
}

pub fn bundle_assets(plan: &BundlePlan, bin_path: impl AsRef<Path>) -> std::io::Result<()> {
    let output_dir = plan.output_dir();
    fs::create_dir_all(&output_dir)?;

    let bin_dest = output_dir.join(
        bin_path
            .as_ref()
            .file_name()
            .unwrap_or_else(|| std::ffi::OsStr::new("deejay")),
    );
    fs::copy(bin_path.as_ref(), bin_dest)?;

    copy_dir("assets", output_dir.join("assets"))?;
    copy_dir("runtime", output_dir.join("runtime"))?;

    let settings_path = output_dir.join("settings.json");
    if !settings_path.exists() {
        let default_settings = Settings::default();
        std::fs::write(
            settings_path,
            serde_json::to_string_pretty(&default_settings).unwrap(),
        )?;
    }

    Ok(())
}

fn copy_dir(from: impl AsRef<Path>, to: impl AsRef<Path>) -> std::io::Result<()> {
    let from = from.as_ref();
    let to = to.as_ref();
    if !from.exists() {
        return Ok(());
    }
    fs::create_dir_all(to)?;
    for entry in WalkDir::new(from) {
        let entry = entry?;
        let rel_path = entry.path().strip_prefix(from).unwrap();
        let dest = to.join(rel_path);
        if entry.file_type().is_dir() {
            fs::create_dir_all(&dest)?;
        } else {
            fs::copy(entry.path(), &dest)?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{bundle_assets, BundlePlan};
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn bundles_assets_and_settings() {
        let dir = tempdir().unwrap();
        let output_dir = dir.path().join("dist");
        fs::write(dir.path().join("dummy"), "bin").unwrap();

        // create temporary assets/runtime
        let assets_dir = dir.path().join("assets");
        fs::create_dir_all(&assets_dir).unwrap();
        fs::write(assets_dir.join("a.txt"), "asset").unwrap();

        let runtime_dir = dir.path().join("runtime");
        fs::create_dir_all(&runtime_dir).unwrap();
        fs::write(runtime_dir.join("r.txt"), "runtime").unwrap();

        let cwd = std::env::current_dir().unwrap();
        std::env::set_current_dir(dir.path()).unwrap();

        let plan = BundlePlan::new("test-target", &output_dir);
        bundle_assets(&plan, "dummy").unwrap();

        std::env::set_current_dir(cwd).unwrap();

        assert!(output_dir.join("test-target/dummy").exists());
        assert!(output_dir.join("test-target/assets/a.txt").exists());
        assert!(output_dir.join("test-target/runtime/r.txt").exists());
        assert!(output_dir.join("test-target/settings.json").exists());
    }
}
