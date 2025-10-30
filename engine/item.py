buffs = [
    dict(id=1, name='测试buff1', icon=1, stock=0, remain_ms=0),
    dict(id=2, name='测试buff2', icon=2, stock=0, remain_ms=100),
]

buff_id_map = {buff['id']: buff for buff in buffs}
buff_name_map = {buff['name']: buff for buff in buffs}