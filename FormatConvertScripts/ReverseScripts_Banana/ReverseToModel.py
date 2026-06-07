from ReverseConfig import vertex_config, preset_config
import struct
import os


def get_category_min_num_max_num_dict_from_ib_file(fc_tmp_ib_file_list):
    # 读取ib文件，并在格式转换后全部堆叠到一起来输出到一个完整的ib文件
    total_num = 0

    tmp_category_min_num_dict = {}
    tmp_category_max_num_dict = {}
    for ib_num in range(len(fc_tmp_ib_file_list)):
        ib_filename = fc_tmp_ib_file_list[ib_num]

        tmp_ib_file = open(reverse_mod_path + ib_filename, "rb")
        tmp_ib_bytearray = bytearray(tmp_ib_file.read())
        tmp_ib_file.close()

        total_num += len(tmp_ib_bytearray)

        i = 0
        max_count = 0
        min_count = 9999999
        while i < len(tmp_ib_bytearray):
            array = tmp_ib_bytearray[i:i + read_pack_stride]
            tmp_byte = struct.pack(write_pack_sign,
                                   struct.unpack(read_pack_sign, array)[0])
            now_count = int.from_bytes(tmp_byte, "little")
            if now_count >= max_count:
                max_count = now_count
            if now_count <= min_count:
                min_count = now_count
            i += read_pack_stride
        print("min count " + str(min_count) + "   max count " + str(max_count))
        tmp_category_min_num_dict[ib_category_list[ib_num]] = min_count
        tmp_category_max_num_dict[ib_category_list[ib_num]] = max_count
    return tmp_category_min_num_dict, tmp_category_max_num_dict


def collect_ib_subtract_offset(filename, offset):
    ib = bytearray()
    with open(filename, "rb") as f:
        data = f.read()
        data = bytearray(data)
        i = 0
        while i < len(data):
            array = data[i:i + read_pack_stride]
            ib += struct.pack(write_pack_sign, struct.unpack(read_pack_sign, array)[0] - offset)
            i += read_pack_stride
    return ib


def get_fmt_str_and_stride_from_element_list():
    # 开始组装fmt文件内容
    fc_tmp_fmt_str = ""

    stride = 0
    element_str = ""
    for num in range(len(element_list)):
        element_name = element_list[num]
        semantic_name = vertex_config[element_name]["semantic_name"]
        semantic_index = vertex_config[element_name]["semantic_index"]
        format = vertex_config[element_name]["format"]
        input_slot = vertex_config[element_name]["input_slot"]
        byte_width = vertex_config[element_name].getint("byte_width")
        aligned_byte_offset = str(stride)
        stride += byte_width
        input_slot_class = vertex_config[element_name]["input_slot_class"]
        instance_data_step_rate = vertex_config[element_name]["instance_data_step_rate"]

        element_str = element_str + "element[" + str(num) + "]:\n"
        element_str = element_str + "  SemanticName: " + semantic_name + "\n"
        element_str = element_str + "  SemanticIndex: " + semantic_index + "\n"
        element_str = element_str + "  Format: " + format + "\n"
        element_str = element_str + "  InputSlot: " + input_slot + "\n"
        element_str = element_str + "  AlignedByteOffset: " + aligned_byte_offset + "\n"
        element_str = element_str + "  InputSlotClass: " + input_slot_class + "\n"
        element_str = element_str + "  InstanceDataStepRate: " + instance_data_step_rate + "\n"

    # combine final fmt str.
    fc_tmp_fmt_str = fc_tmp_fmt_str + "stride: " + str(stride) + "\n"
    fc_tmp_fmt_str = fc_tmp_fmt_str + "topology: " + "trianglelist" + "\n"
    fc_tmp_fmt_str = fc_tmp_fmt_str + "format: " + write_dxgi_format + "\n"
    fc_tmp_fmt_str = fc_tmp_fmt_str + element_str

    return fc_tmp_fmt_str, stride


def split_vb_files(fc_tmp_category_offset_dict, fc_tmp_category_max_num_dict,
                   fc_tmp_vb_file_bytearray, fc_tmp_category_output_name_dict, fc_tmp_stride):
    # 分割VB文件为多个vb文件
    left_offset_num = 0

    for fc_tmp_category in fc_tmp_category_offset_dict:
        print("Processing: " + str(fc_tmp_category))
        fc_tmp_category_max_num = fc_tmp_category_max_num_dict.get(fc_tmp_category)
        vb_file_name = fc_tmp_category_output_name_dict.get(fc_tmp_category)[1]
        print(vb_file_name)

        left_offset = left_offset_num
        right_offset = left_offset_num + fc_tmp_stride * (fc_tmp_category_max_num + 1)

        print("Left: " + str(left_offset/fc_tmp_stride) + "  Right: " + str(right_offset/fc_tmp_stride))
        output_vb_bytearray = fc_tmp_vb_file_bytearray[left_offset:right_offset]

        output_vb_file = open(output_folder + vb_file_name, "wb")
        output_vb_file.write(output_vb_bytearray)
        output_vb_file.close()

        left_offset_num = fc_tmp_stride * (fc_tmp_category_max_num + 1)


def get_category_vb_filename_dict(fc_tmp_mod_files):
    tmp_category_vb_filename_dict = {}
    for vb_category in vb_category_list:
        file_end_str = vb_category + ".buf"

        for filename in fc_tmp_mod_files:
            if filename.endswith(file_end_str):
                tmp_category_vb_filename_dict[vb_category] = filename
    return tmp_category_vb_filename_dict


def get_tmp_ib_file_list(fc_tmp_mod_files):
    tmp_ib_file_list = []
    for ib_category in ib_category_list:
        file_end_str = ib_category + ".ib"

        for filename in fc_tmp_mod_files:
            if filename.endswith(file_end_str):
                tmp_ib_file_list.append(filename)
    return tmp_ib_file_list


def get_vb_byte_array(fc_tmp_category_vb_filename_dict):
    vertex_count = 0
    category_vb_bytearray_list_dict = {}

    for category in fc_tmp_category_vb_filename_dict:
        # 获取buf文件名称
        vb_filename = fc_tmp_category_vb_filename_dict.get(category)
        # 读取buf文件数据
        tmp_vb_file = open(reverse_mod_path + vb_filename, "rb")
        data = bytearray(tmp_vb_file.read())
        tmp_vb_file.close()

        category_bytearray_list = []
        category_stride = category_stride_dict.get(category)
        # 使用 input_stride（含 padding）对齐顶点边界，若无则回退到 category_stride
        input_stride = input_stride_dict.get(category, category_stride)
        print(category)
        print("category_stride(element): " + str(category_stride) + "  input_stride(padded): " + str(input_stride))
        i = 0
        while i < len(data):
            chunk = data[i:i + input_stride]
            # 剥离 padding：只保留 category_stride 字节的有意义数据
            category_bytearray_list.append(chunk[:category_stride])
            i += input_stride
        vertex_count = len(category_bytearray_list)
        category_vb_bytearray_list_dict[category] = category_bytearray_list

    # Merge them into a final bytearray
    tmp_vb_file_bytearray = bytearray()
    print("vertex count:")
    print(vertex_count)
    print(category_vb_bytearray_list_dict.keys())
    for i in range(vertex_count):
        for category in category_vb_bytearray_list_dict:
            bytearray_list = category_vb_bytearray_list_dict.get(category)
            add_byte = bytearray_list[i]
            tmp_vb_file_bytearray += add_byte

    return tmp_vb_file_bytearray


def get_category_output_name_dict(fc_tmp_fmt_str):
    fc_tmp_category_output_name_dict = {}
    for fc_tmp_category in ib_category_list:
        vb_file_name = mod_name + fc_tmp_category + ".vb"
        ib_file_name = mod_name + fc_tmp_category + ".ib"
        fmt_file_name = mod_name + fc_tmp_category + ".fmt"
        fc_tmp_category_output_name_dict[fc_tmp_category] = [ib_file_name, vb_file_name, fmt_file_name]

        # 顺便输出fmt文件
        output_fmt_file = open(output_folder + fmt_file_name, "w")
        output_fmt_file.write(fc_tmp_fmt_str)
        output_fmt_file.close()
    return fc_tmp_category_output_name_dict


def convert_and_output_ib_file(fc_tmp_category_output_name_dict, fc_tmp_category_min_num_dict):
    for category in fc_tmp_category_output_name_dict:
        output_ib_name = fc_tmp_category_output_name_dict.get(category)[0]
        category_min_num = fc_tmp_category_min_num_dict.get(category)
        '''
        这里所谓的offset，就是每个ib文件中出现的最小的数字,
        这里是把原本的Head,Body,Dress的三个ib文件，分别减去其每个ib文件中最小的值，
        使得格式全部变成从0开始的值，这样才能导入blender，
        因为mod格式的ib文件，值是从偏移量那里开始的。
        '''
        original_ib_data = collect_ib_subtract_offset(reverse_mod_path + output_ib_name, category_min_num)
        with open(output_folder + output_ib_name, "wb") as output_ib_file:
            output_ib_file.write(original_ib_data)


def start_reverse():
    # (3) 读取ib文件中，分别最小和最大的数，用于后续转换ib文件时和分割vb文件时提供坐标指示
    category_min_num_dict, category_max_num_dict = get_category_min_num_max_num_dict_from_ib_file(ib_file_list)

    # (4) 获取最终要进行分割处理的vb文件内容
    vb_file_bytearray = get_vb_byte_array(category_vb_filename_dict)

    # (5) 获取最终fmt文件内容
    fmt_str, stride = get_fmt_str_and_stride_from_element_list()

    # (6) 组装出要输出的文件名的字典，用于后续处理,顺便还会输出fmt文件
    category_output_name_dict = get_category_output_name_dict(fmt_str)

    # (7) 把每个ib文件转换成特殊格式后再输出
    convert_and_output_ib_file(category_output_name_dict, category_min_num_dict)

    # (8) 将完整的vb文件分割为多个vb文件
    split_vb_files(category_min_num_dict, category_max_num_dict, vb_file_bytearray, category_output_name_dict, stride)


if __name__ == "__main__":

    # -----------------------------------General--------------------------------------------
    mod_name = preset_config["General"]["mod_name"]

    ib_category_list = preset_config["General"]["ib_category_list"].split(",")
    vb_category_list = preset_config["General"]["vb_category_list"].split(",")
    element_list = preset_config["General"]["element_list"].split(",")

    category_stride_dict = {option: int(value) for option, value in preset_config.items('CategoryStride')}
    print(category_stride_dict)

    # 读取 OutputStride 作为输入 stride（buf 文件可能包含 padding）
    # OutputStride 同时用于 SplitToBuffer.py 的输出填充和 ReverseToModel.py 的输入对齐
    input_stride_dict = {}
    if preset_config.has_section('OutputStride'):
        for option in preset_config.options('OutputStride'):
            val = preset_config.get('OutputStride', option).strip()
            if val:
                input_stride_dict[option] = int(val)
    print("input_stride_dict:")
    print(input_stride_dict)

    # ------------------   format    --------------------------
    read_dxgi_format = preset_config["Format"]["read_dxgi_format"]
    write_dxgi_format = preset_config["Format"]["write_dxgi_format"]

    read_pack_sign = 'H'
    write_pack_sign = 'H'
    read_pack_stride = 2

    if read_dxgi_format == "DXGI_FORMAT_R16_UINT":
        read_pack_stride = 2
        read_pack_sign = 'H'

    if read_dxgi_format == "DXGI_FORMAT_R32_UINT":
        read_pack_stride = 4
        read_pack_sign = 'I'

    if write_dxgi_format == "DXGI_FORMAT_R16_UINT":
        write_pack_sign = 'H'

    if write_dxgi_format == "DXGI_FORMAT_R32_UINT":
        write_pack_sign = 'I'

    '''
    有几个硬参数是灵活变化的，需要在逆向开始前提供
    reverse_mod_path                mod文件所在文件夹
    output_folder                   逆向结果文件输出到哪个目录
    ib_file_list                    ib文件名称列表
    category_vb_filename_dict       {类别:vb文件名称列表}
    '''
    reverse_mod_path = preset_config["General"]["reverse_mod_path"]
    output_folder = reverse_mod_path + "reverse/"
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    # (0) 读取mod文件列表
    mod_files = os.listdir(reverse_mod_path)

    # (1) 读取ib文件名称列表
    ib_file_list = get_tmp_ib_file_list(mod_files)

    # (2) 读取类别:vb文件名称列表
    category_vb_filename_dict = get_category_vb_filename_dict(mod_files)

    # 正式启动逆向
    start_reverse()
