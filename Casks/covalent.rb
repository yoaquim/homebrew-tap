cask "covalent" do
  version "1.2.0"
  sha256 "02b667bfba9988da08ef1bda9e3e60967f89b5f31c0514b7b5ad7a6c2c6ac4d8"

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
