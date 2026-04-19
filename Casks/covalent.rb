cask "covalent" do
  version "1.0.0"
  sha256 "02869be5c31b2a3f4a56fa6b8fed310774ad7653c7ac8946f6f2034c6553f4dd"

  url "https://github.com/yoaquim/covalent/releases/download/v#{version}/Covalent_#{version}_aarch64.dmg"
  name "Covalent"
  desc "Lightweight Markdown viewer with Mermaid diagram support"
  homepage "https://github.com/yoaquim/covalent"

  app "Covalent.app"
end
