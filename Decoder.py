from io import TextIOWrapper
import struct
import sys
import zlib


def decode(filename):
    with open(filename, 'rb') as f:
        png_signature = b'\x89PNG\r\n\x1a\n'
        if f.read(len(png_signature)) != png_signature:
            raise Exception('Invalid PNG Signature')
        chunks = get_chunks(f)
        width, height, bitd, colort, compm, filterm, interlacem = parse_IHDR(b''.join(chunk_data for chunk_type,
                                                                                      chunk_data in chunks if chunk_type == b'IHDR'))
        parsed_IDAT = parse_IDAT(b''.join(chunk_data for chunk_type,
                                          chunk_data in chunks if chunk_type == b'IDAT'))
        recon = []
        bytes_per_pixel = 4
        stride = width * bytes_per_pixel

        i = 0
        for r in range(height):
            filter_type = parsed_IDAT[i]
            i += 1
            for c in range(stride):
                filt_x = parsed_IDAT[i]
                i += 1
                if filter_type == 0:                                            # None
                    recon_x = filt_x
                elif filter_type == 1:                                          # Sub
                    recon_x = filt_x + \
                        recon_a(r, c, recon, stride, bytes_per_pixel)
                elif filter_type == 2:                                          # Up
                    recon_x = filt_x + recon_b(r, c, recon, stride)
                elif filter_type == 3:                                          # Average
                    recon_x = filt_x + \
                        (recon_a(r, c, recon, stride, bytes_per_pixel) +
                         recon_b(r, c, recon, stride)) // 2
                elif filter_type == 4:                                          # Paeth
                    recon_x = filt_x + \
                        paeth_predictor(
                            recon_a(r, c, recon, stride, bytes_per_pixel), recon_b(r, c, recon, stride), recon_c(r, c, recon, stride, bytes_per_pixel))
                else:
                    raise Exception('Unknown filter type: ' + str(filter_type))
                recon.append(recon_x & 0xff)

        return width, height, recon


def get_chunks(file: TextIOWrapper):
    chunks = []
    while True:
        chunk_type, chunk_data = read_chunk(file)
        chunks.append((chunk_type, chunk_data))
        if chunk_type == b'IEND':
            break
    return chunks


def read_chunk(file: TextIOWrapper):
    chunk_length, chunk_type = struct.unpack('>I4s', file.read(8))
    chunk_data = file.read(chunk_length)
    checksum = zlib.crc32(chunk_data, zlib.crc32(
        struct.pack('>4s', chunk_type)))
    chunk_crc, = struct.unpack('>I', file.read(4))
    if chunk_crc != checksum:
        raise Exception('Checksum failed')
    return chunk_type, chunk_data


def parse_IHDR(chunk_data):
    width, height, bitd, colort, compm, filterm, interlacem = struct.unpack(
        '>IIBBBBB', chunk_data)
    if compm != 0:
        raise Exception('Invalid compression method')
    if filterm != 0:
        raise Exception('Invalid filter method')
    if colort != 6:
        raise Exception('Only support truecolor with alpha')
    if bitd != 8:
        raise Exception('Only support a bit depth of 8')
    if interlacem != 0:
        raise Exception('Only support no interlacing')
    return width, height, bitd, colort, compm, filterm, interlacem


def parse_IDAT(chunk_data):
    return zlib.decompress(chunk_data)


def paeth_predictor(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    paeths = sorted([(a, pa), (b, pb), (c, pc)], key=lambda paeth: paeth[1])
    return paeths[0][0]


def recon_a(r, c, recon, stride, bytes_per_pixel):
    return recon[r * stride + c - bytes_per_pixel] if c >= bytes_per_pixel else 0


def recon_b(r, c, recon, stride):
    return recon[(r-1) * stride + c] if r > 0 else 0


def recon_c(r, c, recon, stride, bytes_per_pixel):
    return recon[(r-1) * stride + c - bytes_per_pixel] if r > 0 and c >= bytes_per_pixel else 0


if __name__ == '__main__':
    try:
        width, height, recon = decode(sys.argv[1])

        import matplotlib.pyplot as plt
        import numpy as np
        plt.imshow(np.array(recon).reshape((height, width, 4)))
        plt.savefig('Decoded_Image.png')

    except IndexError:
        print('Args not valid.\nDecoder usage:\n\tDecoder.py PATH\\RELATIVE\\TO\\PNG')
