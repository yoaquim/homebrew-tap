cask "covalent" do
  version "1.8.2"
  sha256 "6bc10d879657aec24ae2a0c3c637e5b7af9b7694ae5f38ecc8a31b2cf0904139"

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
