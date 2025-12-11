mod bundle;
mod crash;
mod settings;
mod version;

use std::path::PathBuf;

use clap::{Parser, Subcommand};
use settings::Settings;

use crate::bundle::{bundle_assets, BundlePlan};
use crate::crash::install_panic_hook;
use crate::version::current_version;

#[derive(Debug, Parser)]
#[command(author, version, about = "Cross-platform device/buffer configuration helper", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// Device identifier to use for audio IO
    #[arg(long)]
    device: Option<String>,

    /// Buffer size in frames
    #[arg(long)]
    buffer_frames: Option<u32>,

    /// Sample rate for the session
    #[arg(long)]
    sample_rate: Option<u32>,

    /// Persist any provided configuration overrides to settings.json
    #[arg(long)]
    save: bool,

    /// Override the default crash log path
    #[arg(long)]
    crash_log: Option<PathBuf>,
}

#[derive(Debug, Subcommand)]
enum Commands {
    /// Bundle assets and runtime dependencies into a dist/ folder
    Bundle {
        /// Target triple to place artifacts under (defaults to host target)
        #[arg(long, default_value_t = default_target())]
        target: String,
        /// Optional output directory (defaults to dist/)
        #[arg(long, default_value = "dist")]
        dist_dir: String,
        /// Path to the already-built binary to bundle
        #[arg(long, default_value = "target/release/deejay")]
        binary: String,
    },
}

fn default_target() -> String {
    std::env::var("TARGET").unwrap_or_else(|_| {
        format!(
            "{}-unknown-{}",
            std::env::consts::ARCH,
            std::env::consts::OS.replace(' ', "")
        )
    })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    let version = current_version().to_string();

    let crash_log = cli
        .crash_log
        .unwrap_or_else(|| PathBuf::from("crash.log"));
    install_panic_hook(crash_log, &version);

    if let Some(command) = cli.command {
        match command {
            Commands::Bundle {
                target,
                dist_dir,
                binary,
            } => {
                let plan = BundlePlan::new(target, dist_dir);
                bundle_assets(&plan, binary)?;
                println!(
                    "Bundled assets and runtime dependencies to {}",
                    plan.output_dir().display()
                );
                return Ok(());
            }
        }
    }

    let mut settings = Settings::load()?;

    if let Some(device) = cli.device {
        settings.device = device;
    }

    if let Some(buffer_frames) = cli.buffer_frames {
        settings.buffer_frames = buffer_frames;
    }

    if let Some(sample_rate) = cli.sample_rate {
        settings.sample_rate = sample_rate;
    }

    if cli.save {
        settings.save()?;
    }

    println!(
        "DeeJay v{}\ndevice: {}\nbuffer_frames: {}\nsample_rate: {}",
        version, settings.device, settings.buffer_frames, settings.sample_rate
    );

    Ok(())
}
