cask "dualapp" do
  arch arm: "aarch64", intel: "x86_64"

  version "2.0.0"
  sha256 arm:   "1111111111111111111111111111111111111111111111111111111111111111",
         intel: "2222222222222222222222222222222222222222222222222222222222222222"

  url "https://github.com/example/dualapp/releases/download/v#{version}/DualApp_#{version}_#{arch}.dmg"
  name "DualApp"
  desc "Example app shipping arm and intel builds"
  homepage "https://github.com/example/dualapp"

  app "DualApp.app"
end
