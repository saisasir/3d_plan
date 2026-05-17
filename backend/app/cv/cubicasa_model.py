import torch
import torch.nn as nn
import torch.nn.functional as F

class Residual(nn.Module):
    def __init__(self, ins, outs):
        super(Residual, self).__init__()
        self.convBlock = nn.Sequential(
            nn.BatchNorm2d(ins),
            nn.ReLU(inplace=True),
            nn.Conv2d(ins, outs // 2, 1),
            nn.BatchNorm2d(outs // 2),
            nn.ReLU(inplace=True),
            nn.Conv2d(outs // 2, outs // 2, 3, 1, 1),
            nn.BatchNorm2d(outs // 2),
            nn.ReLU(inplace=True),
            nn.Conv2d(outs // 2, outs, 1)
        )
        if ins != outs:
            self.skipStep = nn.Conv2d(ins, outs, 1)
        else:
            self.skipStep = None

    def forward(self, x):
        residual = x
        if self.skipStep is not None:
            residual = self.skipStep(x)
        out = self.convBlock(x)
        return out + residual

class Hourglass(nn.Module):
    def __init__(self, n, f):
        super(Hourglass, self).__init__()
        self.up1 = Residual(f, f)
        self.low1 = nn.Sequential(
            nn.MaxPool2d(2, 2),
            Residual(f, f)
        )
        if n > 1:
            self.low2 = Hourglass(n - 1, f)
        else:
            self.low2 = Residual(f, f)
        self.low3 = Residual(f, f)
        self.up2 = nn.Upsample(scale_factor=2, mode='nearest')

    def forward(self, x):
        up1 = self.up1(x)
        low1 = self.low1(x)
        low2 = self.low2(low1)
        low3 = self.low3(low2)
        up2 = self.up2(low3)
        return up1 + up2

class CubiCasaModel(nn.Module):
    """
    Simplified Stacked Hourglass Network for CubiCasa5K Inference.
    Trained for Multi-Task: Segmentation + Heatmaps.
    """
    def __init__(self, nstack=2, nfeatures=128, nclasses=[44, 21, 2]):
        super(CubiCasaModel, self).__init__()
        self.nstack = nstack
        self.pre = nn.Sequential(
            nn.Conv2d(3, 64, 7, 2, 3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            Residual(64, 128),
            nn.MaxPool2d(2, 2),
            Residual(128, 128),
            Residual(128, nfeatures)
        )
        
        self.hgs = nn.ModuleList([
            nn.Sequential(Hourglass(4, nfeatures)) for _ in range(nstack)
        ])
        
        self.features = nn.ModuleList([
            nn.Sequential(
                Residual(nfeatures, nfeatures),
                nn.Conv2d(nfeatures, nfeatures, 1),
                nn.BatchNorm2d(nfeatures),
                nn.ReLU(inplace=True)
            ) for _ in range(nstack)
        ])
        
        # Heads for different tasks (Rooms, Openings, Walls)
        self.outs = nn.ModuleList([
            nn.ModuleList([
                nn.Conv2d(nfeatures, nc, 1) for nc in nclasses
            ]) for _ in range(nstack)
        ])
        
        self.merge_features = nn.ModuleList([
            nn.Conv2d(nfeatures, nfeatures, 1) for _ in range(nstack - 1)
        ])
        self.merge_preds = nn.ModuleList([
            nn.Conv2d(sum(nclasses), nfeatures, 1) for _ in range(nstack - 1)
        ])

    def forward(self, x):
        x = self.pre(x)
        combined_outputs = []
        for i in range(self.nstack):
            hg = self.hgs[i](x)
            feature = self.features[i](hg)
            preds = [out(feature) for out in self.outs[i]]
            combined_outputs.append(preds)
            
            if i < self.nstack - 1:
                x = x + self.merge_features[i](feature) + self.merge_preds[i](torch.cat(preds, 1))
        
        return combined_outputs
