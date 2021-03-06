import re
import torch
from torch import nn
from torch.nn import functional as F
import math
from dataloader_packed import PatientDataset
import torch.nn.utils.rnn as rnn_utils
from transformers import AutoTokenizer, AutoModel

from tqdm import tqdm
import numpy as np
import os
from collections import deque
import torch.optim as optim
   
class mllt(nn.Module):
    def __init__(self, ):
        super(mllt, self).__init__()
        self.hidden_size = 768
        self.encoder = AutoModel.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
        self.fc_key = nn.Linear(self.hidden_size,self.hidden_size//2)
        self.fc_query = nn.Linear(self.hidden_size,self.hidden_size//2)
        self.fc_value = nn.Linear(self.hidden_size,self.hidden_size//2)

        self.MLPs = nn.Sequential(
        nn.Linear(self.hidden_size//2, 3),
        )
        self.drop_out = nn.Dropout(0.3)
        self.sigmoid = nn.Sigmoid()

    def cross_attention(self,v,c):
        B, Nt, E = v.shape
        v = v / math.sqrt(E)
        # print("v :", v)
        # print("c :", c)

        v = self.drop_out(self.fc_key(v))
        c = self.drop_out(self.fc_query(c))
        g = torch.bmm(v, c.transpose(-2, -1))

        m = F.max_pool2d(g,kernel_size = (1,g.shape[-1])).squeeze(1)  # [b, l, 1]

        b = torch.softmax(m, dim=1)  # [b, l, 1]
        # print("b: ",b[[1],:,:].squeeze().squeeze())
        return b    
    def approximation(self, Ot,label_token,self_att):
        Ot_E_batch = self.encoder(**Ot).last_hidden_state
        label_embedding = self.encoder(**label_token).last_hidden_state.sum(1)
        if self_att == "self_att":
            attention_weights =  self.cross_attention(Ot_E_batch,Ot_E_batch)
            Ot_E_batch = self.drop_out(self.fc_value(Ot_E_batch))
            Ztd =   self.drop_out(Ot_E_batch * attention_weights).sum(1)
            return Ztd        
        elif self_att == "cross_att":
            attention_weights = self.cross_attention(Ot_E_batch,label_embedding.unsqueeze(0).repeat(Ot_E_batch.shape[0],1,1))
            Ot_E_batch = self.drop_out(self.fc_value(Ot_E_batch))
            Ztd =   self.drop_out(Ot_E_batch * attention_weights).sum(1)
            return Ztd   
        else:
            return self.drop_out(self.fc_value(Ot_E_batch)).mean(1) 
 



    def forward(self,Ot,label_embedding,self_att):

        Ztd = self.approximation(Ot,label_embedding,self_att)
           
        # Yt =  self.sigmoid(self.drop_out(self.MLPs(Ztd)))
        return Ztd
        # return Yt

   



