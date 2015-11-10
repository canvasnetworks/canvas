from compressor.storage import CompressorFileStorage

class CanvasFileStorage(CompressorFileStorage):
    def url(self, path):
        return "//canvas-dynamic-assets.s3.amazonaws.com/static/" + path

