class Prism < Formula
  desc "Semantic Search for Local Datasets (YOLO + SigLIP)"
  homepage "https://github.com/sjanney/prism"
  url "https://github.com/sjanney/prism/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA"
  license "MIT"

  depends_on "go" => :build
  depends_on "python@3.11"
  depends_on "protobuf"

  def install
    # Install Python dependencies
    system "pip3", "install", "-r", "backend/requirements.txt"
    
    # Generate gRPC code
    system "./codegen.sh"

    # Build Go frontend
    cd "frontend" do
      system "go", "build", "-o", bin/"prism", "."
    end

    # Install backend scripts
    libexec.install Dir["backend/*"]
    # We could wrap the launcher here
  end

  test do
    system "#{bin}/prism", "--help"
  end
end
