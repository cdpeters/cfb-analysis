from cfb_pipeline.types import Region


def global_to_local_region(
    region: Region,
    parent_region: Region,
) -> Region:
    """Convert a region in global coordinates into coordinates relative to a parent region."""
    region_left, region_top, region_right, region_bottom = region
    parent_left, parent_top, _, _ = parent_region

    return (
        region_left - parent_left,
        region_top - parent_top,
        region_right - parent_left,
        region_bottom - parent_top,
    )

def local_to_global_region(
    region: Region,
    parent_region: Region,
) -> Region:
    """Convert a region in coordinates relative to a parent region into global coordinates."""
    region_left_local, region_top_local, region_right_local, region_bottom_local = region
    parent_left_global, parent_top_global, _, _ = parent_region

    return (
        region_left_local + parent_left_global,
        region_top_local + parent_top_global,
        region_right_local + parent_left_global,
        region_bottom_local + parent_top_global,
    )
