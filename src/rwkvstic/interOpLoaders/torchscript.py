from rwkvstic.rwkvMaster import RWKVMaster
from rwkvstic.agnostic.samplers.numpy import npsample


def initTorchScriptFile(path, tokenizer=None):
    import torch

    embed = path.split("-")[2].split(".")[0]
    layers = path.split("-")[1]
    mymodel = torch.jit.load(path)
    device = torch.device("cuda" if "gpu" in path else "cpu")
    dtype = (
        torch.bfloat16
        if "bfloat16" in path
        else torch.float32
        if "float32" in path
        else torch.float16
        if "float16" in path
        else torch.float64
    )
    print("input shape", dtype)

    class InterOp:
        RnnOnly = not True

        def forward(self, x, y):

            mm, nn = mymodel(torch.LongTensor(x), y)

            return mm.cpu(), nn

    model = InterOp()
    emptyState = torch.tensor(
        [[[0.01] * int(embed)] * 5] * int(layers), dtype=dtype, device=device
    )

    def initTensor(x):
        return torch.tensor(x, dtype=dtype, device=device)

    useSampler = "sampler" not in path

    def intTensor(x):
        return [x] if type(x) == int else x

    return RWKVMaster(
        model,
        emptyState,
        initTensor,
        intTensor,
        npsample if useSampler else None,
        tokenizer,
    )
