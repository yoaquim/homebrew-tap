cask "covalent" do
  version "1.6.2"
  sha256 "e6f2c4c256cd128c27526765e6db4b509dc61fa18b5777c42aefafcfadd0e129"

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
