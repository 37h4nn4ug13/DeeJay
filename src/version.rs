/// Return the build version, preferring the BUILD_VERSION env var if present.
pub fn current_version() -> &'static str {
    option_env!("BUILD_VERSION").unwrap_or(env!("CARGO_PKG_VERSION"))
}

#[cfg(test)]
mod tests {
    use super::current_version;

    #[test]
    fn uses_package_version() {
        // BUILD_VERSION is not set in tests by default
        assert_eq!(current_version(), env!("CARGO_PKG_VERSION"));
    }
}
