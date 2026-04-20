cask "covalent" do
  version "1.5.0"
  sha256 "8d49090ec5911045922ad936c037cc637c55a7639349955fd3c9743aefc72adb"

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
