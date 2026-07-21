from src.shared.constants.media_sizes import MediaSize


def convert_bytes_to_target(sizes: int, target_unit: MediaSize) -> float:
    match target_unit:
        case MediaSize.BYTES:
            return sizes
        case MediaSize.KB:
            return sizes / 1024
        case MediaSize.MB:
            return sizes / (1024 * 1024)
        case MediaSize.GB:
            return sizes / (1024 * 1024 * 1024)
        case MediaSize.TB:
            return sizes / (1024 * 1024 * 1024 * 1024)
        case _:
            raise ValueError(f"Invalid unit: {target_unit}")


def convert_current_unit_to_bytes(sizes: float, current_unit: MediaSize) -> int:
    match current_unit:
        case MediaSize.BYTES:
            return int(sizes)
        case MediaSize.KB:
            return int(sizes * 1024)
        case MediaSize.MB:
            return int(sizes * (1024 * 1024))
        case MediaSize.GB:
            return int(sizes * (1024 * 1024 * 1024))
        case MediaSize.TB:
            return int(sizes * (1024 * 1024 * 1024 * 1024))
        case _:
            raise ValueError(f"Invalid unit: {current_unit}")
