from rwkvstic.agnostic.backends.base import module
from typing import Dict


def AgnosticRWKV(ops: module, *args):
    class myRWKV(ops.module):

        @ ops.initfunc
        def __init__(self, w: Dict[str, ops.TensorType]):
            super(myRWKV, self).__init__()
            print("Legacy RWKV")

            for x in ops.__dict__.keys():
                self.__dict__[x] = ops.__dict__[x]
            self.postprocess0: ops.VectorType = (w["ln_out.weight"])
            self.postprocess1: ops.VectorType = (w["ln_out.bias"])
            self.postprocess2: ops.VectorType = (w["head.weight"])
            self.emb: ops.MatrixType = w["emb.weight"]
            self.emb1: ops.VectorType = w["blocks.0.ln0.weight"]
            self.emb2: ops.VectorType = w["blocks.0.ln0.bias"]
            self.ln1w: ops.VectorType = ops.mnstack(
                [w[f"blocks.{x}.ln1.weight"] for x in range(ops.n_layers)])
            self.ln1b: ops.VectorType = ops.mnstack(
                [w[f"blocks.{x}.ln1.bias"] for x in range(ops.n_layers)])
            self.ln2w: ops.VectorType = ops.mnstack(
                [w[f"blocks.{x}.ln2.weight"] for x in range(ops.n_layers)])
            self.ln2b: ops.VectorType = ops.mnstack(
                [w[f"blocks.{x}.ln2.bias"] for x in range(ops.n_layers)])
            self.time_decay: ops.VectorType = ops.mnstack([
                w[f"blocks.{x}.att.time_decay"] for x in range(ops.n_layers)])
            self.time_first: ops.VectorType = ops.mnstack([
                w[f"blocks.{x}.att.time_first"] for x in range(ops.n_layers)])
            self.kktk: ops.VectorType = ops.mnstack(
                [w[f"blocks.{x}.att.time_mix_k"] for x in range(ops.n_layers)])
            self.vvtv: ops.VectorType = ops.mnstack(
                [w[f"blocks.{x}.att.time_mix_v"] for x in range(ops.n_layers)])
            self.rrtr: ops.VectorType = ops.mnstack(
                [w[f"blocks.{x}.att.time_mix_r"] for x in range(ops.n_layers)])
            self.key: ops.MatrixType = ops.mnstack(
                [w[f"blocks.{x}.att.key.weight"] for x in range(ops.n_layers)])
            self.value: ops.MatrixType = ops.mnstack(
                [w[f"blocks.{x}.att.value.weight"] for x in range(ops.n_layers)])
            self.receptance: ops.MatrixType = ops.mnstack([
                w[f"blocks.{x}.att.receptance.weight"] for x in range(ops.n_layers)])
            self.outputvv: ops.MatrixType = ops.mnstack([
                w[f"blocks.{x}.att.output.weight"] for x in range(ops.n_layers)])
            self.time_mix_k_ffn: ops.VectorType = ops.mnstack([
                w[f"blocks.{x}.ffn.time_mix_k"] for x in range(ops.n_layers)])
            self.time_mix_r_ffn: ops.VectorType = ops.mnstack([
                w[f"blocks.{x}.ffn.time_mix_r"] for x in range(ops.n_layers)])
            self.key_ffn: ops.MatrixType = ops.mnstack(
                [w[f"blocks.{x}.ffn.key.weight"] for x in range(ops.n_layers)])
            self.receptance_ffn: ops.MatrixType = ops.mnstack([
                w[f"blocks.{x}.ffn.receptance.weight"] for x in range(ops.n_layers)])
            self.value_ffn: ops.MatrixType = ops.mnstack([
                w[f"blocks.{x}.ffn.value.weight"] for x in range(ops.n_layers)])

            if ops.useLogFix:
                self.processLayer = self.processLayerx

        def processLayerx(self, k, v, rz, state, xx: int, i: int):
            ww = self.time_first[xx] + k[i]
            p = self.maximum(state[4], ww)

            e1 = self.exp(self.subtract((state[4]), p))

            e2 = self.exp(self.subtract(ww, p))

            a = self.add(self.multiply(e1, (state[2])),
                         self.multiply(e2, v[i]))

            b = self.add(self.multiply(
                e1, (state[3])), e2)

            wwn = self.add((
                state[4]), self.time_decay[xx])

            p1 = self.maximum(wwn, k[i])

            e11 = self.exp(self.subtract(wwn, p1))

            e21 = self.exp(self.subtract(k[i], p1))

            outb = self.add(self.multiply(e11, (state[2])),
                            self.multiply(e21, v[i]))

            outc = self.add(self.multiply(
                e11, (state[3])), e21)

            # state[2:5] = ops.stack((outb, outc, p1))

            state = self.scatter(state, self.scatterindices[0], ops.stack(
                (outb, outc, p1)))
            wkv = self.divide(a, b)
            rz = self.arrayPush(rz, wkv, i)
            return rz, state

        def processLayer(self, k, v, rz, state, xx: int, i: int):
            ki = ops.exp(k[i])
            wrd = ops.divide(
                ops.add(state[2], ops.multiply(ops.multiply(ki, v[i]), ops.exp(self.time_first[xx]))), ops.add(state[3], ops.multiply(ki, ops.exp(self.time_first[xx]))))

            state = ops.scatter(state, ops.scatterindices[1], ops.multiply(ops.exp(self.time_decay[xx]), ops.add(
                state[2:4], ops.stack((ops.multiply(
                    v[i], ki), ki)))))

            rz = ops.arrayPush(rz, wrd, i)
            return rz, state

        @ ops.layerdef
        def doLayer(self, x, state, xx: int):

            xy = self.layernorm(x, self.ln1w[xx], self.ln1b[xx])

            tc = self.push(self.roll(xy),  state[0])

            k = self.matvec(
                self.key[xx], self.lerp(tc, xy, self.kktk[xx]))

            v = self.matvec(self.value[xx], self.lerp(
                tc, xy, self.vvtv[xx]))

            rr = self.matvec(
                self.receptance[xx], self.lerp(tc, xy, self.rrtr[xx]))

            r = self.logistical(rr)

            rz = self.emptyarray(self.len(x))

            for i in self.rng(self.len(x)):

                rz, state = self.processLayer(k, v, rz, state, xx, i)

            mvv = self.add(x, self.matvec(
                self.outputvv[xx], self.multiply(r, self.stack(rz))))

            ddd = self.layernorm(mvv, self.ln2w[xx], self.ln2b[xx])

            rc = self.push(self.roll(ddd), state[1])
            # self.arrayPush(state, xy[-1], 0)
            # self.arrayPush(state, ddd[-1], 1)
            state = self.scatter(state, self.scatterindices[2], ops.stack(
                (xy[-1], ddd[-1])))

            km = self.relu(self.matvec(self.key_ffn[xx], self.lerp(
                rc, ddd, self.time_mix_k_ffn[xx])))

            rt = self.logistical((self.matvec(self.receptance_ffn[xx], self.lerp(
                rc, ddd, self.time_mix_r_ffn[xx]))))

            rvm = self.matvec(self.value_ffn[xx], self.multiply(km, km))

            x = self.add(mvv, self.multiply(
                rvm, rt))

            return x,  state

        @ ops.mainfunc
        def forward(self, x, state):
            g = self.getIndex(self.emb, x)
            x = self.layernorm(
                self.processEmbed(g),
                self.emb1, self.emb2)

            for i in self.rng(self.len(state)):

                x, rstate = self.doLayer(
                    x, state[i], i)
                state = self.scatter(state, i, rstate)

            x = self.matvec(self.postprocess2, self.layernorm(x, self.postprocess0,
                                                              self.postprocess1))

            return self.postProcessTensor(self.pop(x)), state

        # for keras stuff, ignore this if you are not using keras
        def call(self, *args, **kwds):
            del kwds["training"]
            return self.forward(*args, **kwds)
    returnObject: myRWKV = ops.postProcessModule(myRWKV(*args))
    return returnObject
