import json

from awaits.awaitable import awaitable

from app.core.constructor.constructor import ConstructorAbstract
from app.models.constructor import Constructor


class PythonConstructor(ConstructorAbstract):

    @staticmethod
    @awaitable
    def run(executor, env, index, path, params, req_params, constructor: Constructor, **kwargs):
        try:
            executor.append(f"当前路径: {path}, 第{index + 1}条{ConstructorAbstract.get_name(constructor)}")
            script = json.loads(constructor.constructor_json)
            command = script['command']
            executor.append(f"当前{ConstructorAbstract.get_name(constructor)}类型为python脚本\n{command}")
            loc = dict()
            exec(command, loc)
            py_data = loc[constructor.value]
            if not isinstance(py_data, str):
                py_data = json.dumps(params[constructor.value], ensure_ascii=False)
            executor.append(
                f"当前{ConstructorAbstract.get_name(constructor)}返回变量: {constructor.value}\n返回值:\n {py_data}\n")
        except Exception as e:
            raise Exception(
                f"{path}->{constructor.name} 第{index + 1}个{ConstructorAbstract.get_name(constructor)}执行失败: {e}")
