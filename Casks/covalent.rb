cask "covalent" do
  version "1.8.1"
  sha256 "011221d127a3b53075e97eca96e69e5da2dcf0cfc6e977ffcb2ac7b94c1db098"

  url "https://github.com/yoaquim/covalent/releases/download/v#{version}/Covalent_#{version}_aarch64.dmg"
  name "Covalent"
  desc "Native Markdown viewer with math, diagrams, and syntax highlighting"
  homepage "https://github.com/yoaquim/covalent"

  app "Covalent.app"

  postflight do
    system_command "/usr/bin/xattr",
         args: ["-cr", "#{appdir}/Covalent.app"]
  end
end
