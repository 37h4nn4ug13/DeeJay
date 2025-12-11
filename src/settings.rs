use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SettingsError {
    #[error("failed to read settings file: {0}")]
    Read(#[from] std::io::Error),
    #[error("failed to parse settings file: {0}")]
    Parse(#[from] serde_json::Error),
}

#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
pub struct Settings {
    pub device: String,
    pub buffer_frames: u32,
    pub sample_rate: u32,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            device: "default".to_string(),
            buffer_frames: 512,
            sample_rate: 48_000,
        }
    }
}

impl Settings {
    pub fn path() -> PathBuf {
        Path::new("settings.json").to_path_buf()
    }

    pub fn load() -> Result<Self, SettingsError> {
        let path = Self::path();
        if !path.exists() {
            return Ok(Self::default());
        }

        let contents = fs::read_to_string(&path)?;
        let settings = serde_json::from_str(&contents)?;
        Ok(settings)
    }

    pub fn save(&self) -> Result<(), SettingsError> {
        let payload = serde_json::to_string_pretty(self)?;
        fs::write(Self::path(), payload)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::Settings;
    use tempfile::tempdir;

    #[test]
    fn round_trips_settings() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("settings.json");
        let mut settings = Settings::default();
        settings.device = "loopback".into();
        settings.buffer_frames = 1024;

        let previous = std::env::current_dir().unwrap();
        std::env::set_current_dir(dir.path()).unwrap();

        settings.save().unwrap();
        let loaded = Settings::load().unwrap();

        std::env::set_current_dir(previous).unwrap();

        assert_eq!(settings, loaded);
        assert!(file.exists());
    }
}
