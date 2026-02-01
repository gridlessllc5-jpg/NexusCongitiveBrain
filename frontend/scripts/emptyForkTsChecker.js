// Stub for ForkTsCheckerWebpackPlugin to bypass ajv-keywords formatMinimum errors during build
class EmptyForkTsCheckerPlugin {
  apply() {
    // no-op
  }
}

module.exports = EmptyForkTsCheckerPlugin;
