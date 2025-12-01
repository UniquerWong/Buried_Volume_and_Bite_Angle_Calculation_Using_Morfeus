import os
import math

# ===== 配置 =====
FOLDER_PATH = "."  # 放 xyz 文件的文件夹
OUTPUT_SUFFIX = "_d"  # 输出文件后缀：原名 + 这个后缀 + ".xyz"

# 认为是“中心金属”的元素
CENTER_METALS = {"Ir", "Rh", "Pd", "Pt", "Ni", "Co", "Fe", "Ru", "Os"}

# 距离阈值（可按需要微调）
CO_BOND_MIN = 1.00  # C-O 最小键长
CO_BOND_MAX = 1.30  # C-O 最大键长（终端 CO 一般 ~1.15 Å 左右）
M_C_MAX = 2.20      # M-C 最大键长（Ir–CO、Rh–CO 大概 1.8–2.1 Å）

def distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    )

def read_xyz(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f]

    if len(lines) < 2:
        raise ValueError("XYZ 文件行数不足")

    try:
        n_atoms = int(lines[0].strip())
    except Exception as e:
        raise ValueError(f"首行不是整数原子数: {e}")

    comment = lines[1]
    atom_lines = lines[2:2 + n_atoms]

    if len(atom_lines) < n_atoms:
        raise ValueError(f"声明原子数为 {n_atoms}，但实际只有 {len(atom_lines)} 行")

    elements = []
    coords = []
    for line in atom_lines:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 4:
            raise ValueError(f"原子行格式错误: {line}")
        elem = parts[0]
        x, y, z = map(float, parts[1:4])
        elements.append(elem)
        coords.append((x, y, z))

    return elements, coords, comment, lines[2 + n_atoms:]  # extra_lines 保留原文件可能的尾部

def write_xyz(path, elements, coords, comment, extra_lines=None):
    n_atoms = len(elements)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{n_atoms}\n")
        f.write(f"{comment}\n")
        for elem, (x, y, z) in zip(elements, coords):
            f.write(f"{elem:2s}  {x:12.6f}  {y:12.6f}  {z:12.6f}\n")
        if extra_lines:
            for line in extra_lines:
                f.write(line + "\n")

def find_metal_center(elements, coords):
    """自动找第一个中心金属的索引（0-based），找不到返回 None"""
    for i, elem in enumerate(elements):
        if elem in CENTER_METALS:
            return i
    return None

def find_CO_pairs(elements, coords, metal_index):
    """
    找 M–CO 配体：
    - C-O 距离在 CO_BOND_MIN ~ CO_BOND_MAX 之间
    - C 到金属距离 < M_C_MAX
    返回: [(c_idx, o_idx), ...]，索引为 0-based
    """
    co_pairs = []

    # 先找所有 C-O 配对
    for i, elem_i in enumerate(elements):
        if elem_i != "C":
            continue
        for j, elem_j in enumerate(elements):
            if elem_j != "O":
                continue
            d_co = distance(coords[i], coords[j])
            if CO_BOND_MIN <= d_co <= CO_BOND_MAX:
                # 再检查 C 到金属的距离
                if metal_index is not None:
                    d_mc = distance(coords[i], coords[metal_index])
                    if d_mc <= M_C_MAX:
                        co_pairs.append((i, j))
                else:
                    # 没有金属中心信息，就先把 C-O 当作 CO 记录下来
                    co_pairs.append((i, j))

    # 去重（避免 C-O 和 O-C 之类的重复；这里其实不会，但保险）
    unique_pairs = []
    seen = set()
    for c_idx, o_idx in co_pairs:
        key = tuple(sorted((c_idx, o_idx)))
        if key not in seen:
            seen.add(key)
            unique_pairs.append((c_idx, o_idx))

    return unique_pairs

def process_xyz_file(path):
    try:
        elements, coords, comment, extra_lines = read_xyz(path)
    except Exception as e:
        print(f"[跳过] 读取失败 {os.path.basename(path)}: {e}")
        return

    n_atoms = len(elements)
    if n_atoms == 0:
        print(f"[跳过] {os.path.basename(path)} 原子数为 0")
        return

    metal_index = find_metal_center(elements, coords)
    if metal_index is None:
        print(f"[跳过] {os.path.basename(path)} 中未找到中心金属 {CENTER_METALS}")
        return

    co_pairs = find_CO_pairs(elements, coords, metal_index)

    if len(co_pairs) < 2:
        print(f"[警告] {os.path.basename(path)} 只找到 {len(co_pairs)} 个 CO 配体，少于 2 个，不做删除")
        return

    # 只删掉前两个 CO 配体
    pairs_to_delete = co_pairs[:2]

    # 要删除的原子索引（0-based）
    delete_indices = set()
    for c_idx, o_idx in pairs_to_delete:
        delete_indices.add(c_idx)
        delete_indices.add(o_idx)

    # 根据索引保留原子
    new_elements = []
    new_coords = []
    for i, (elem, coord) in enumerate(zip(elements, coords)):
        if i in delete_indices:
            continue
        new_elements.append(elem)
        new_coords.append(coord)

    # 生成输出文件名
    base, ext = os.path.splitext(path)
    new_path = base + OUTPUT_SUFFIX + ext

    write_xyz(new_path, new_elements, new_coords, comment, extra_lines)

    print(
        f"[完成] {os.path.basename(path)}: "
        f"原子数 {n_atoms} -> {len(new_elements)}，"
        f"删除 CO 配体个数 = {len(pairs_to_delete)}，输出文件: {os.path.basename(new_path)}"
    )

def main():
    for file_name in os.listdir(FOLDER_PATH):
        if not file_name.lower().endswith(".xyz"):
            continue
        full_path = os.path.join(FOLDER_PATH, file_name)
        process_xyz_file(full_path)

if __name__ == "__main__":
    main()
