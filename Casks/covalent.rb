cask "covalent" do
  version "1.8.2"
  sha256 "7c54f61ef32392c1a17b43b053e987f1ae7f273d479d9184d2daacf3f8d2b124"

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
