cask "covalent" do
  version "1.3.0"
  sha256 "ebccf4438c8f54064a70a6b12e01600d59216a16a2ab67e84aa9b6b20e3c3c18"

  url "https://github.com/yoaquim/covalent/releases/download/v#{version}/Covalent_#{version}_aarch64.dmg"
  name "Covalent"
  desc "Lightweight Markdown viewer with Mermaid diagram support"
  homepage "https://github.com/yoaquim/covalent"

  app "Covalent.app"

  postflight do
    system_command "/usr/bin/xattr",
                   args: ["-cr", "#{appdir}/Covalent.app"]
  end
end
