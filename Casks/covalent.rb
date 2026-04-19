cask "covalent" do
  version "1.0.0"
  sha256 :no_check

  url "https://github.com/yoaquim/covalent/releases/download/v#{version}/Covalent_#{version}_aarch64.dmg"
  name "Covalent"
  desc "Lightweight Markdown viewer with Mermaid diagram support"
  homepage "https://github.com/yoaquim/covalent"

  app "Covalent.app"
end
