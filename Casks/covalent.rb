cask "covalent" do
  version "1.1.0"
  sha256 "6061d499634c25a9ae3a0b5c2d1923dc2fac4ec63d44dbf25c38c4b63cf95688"

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
