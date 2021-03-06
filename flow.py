import math 
import torch
import torch.nn as nn
import torch.nn.functional as F
from symmetrize import Symmetrize

class MongeAmpereFlow(nn.Module):
    '''
    continuous-time Brenier flow
    dx/dt = du(x)/dx
    dlnp(x)/dt = -d^2 u(x)/dx^2 
    '''
    def __init__(self, net, epsilon, Nsteps, device='cpu', name=None):
        super(MongeAmpereFlow, self).__init__()
        self.device = device
        if name is None:
            self.name = 'MongeAmpereFlow'
        else:
            self.name = name
        self.net = net 
        self.dim = net.dim
        self.epsilon = epsilon 
        self.Nsteps = Nsteps

    def integrate(self, x, logp, sign=1, epsilon=None, Nsteps=None):
        #default values
        if epsilon is None:
            epsilon = self.epsilon 
        if Nsteps is None:
            Nsteps = self.Nsteps

        #integrate ODE for x and logp(x)
        def ode(x):
            #special to Simple_MLP
            if isinstance(self.net, Symmetrize): self.net.update_perm(x)
            return sign*epsilon*self.net.grad(x), -sign*epsilon*self.net.laplacian(x)

        #rk4
        for step in range(Nsteps):
            k1_x, k1_logp = ode(x)
            k2_x, k2_logp = ode(x+k1_x/2)
            k3_x, k3_logp = ode(x+k2_x/2)
            k4_x, k4_logp = ode(x+k3_x)

            x = x + (k1_x/6.+k2_x/3. + k3_x/3. +k4_x/6.) 
            logp = logp + (k1_logp/6. + k2_logp/3. + k3_logp/3. + k4_logp/6.)
                
        return x, logp

    def sample(self, batch_size, sigma=1.0):
        #initial value from Gaussian
        x = torch.Tensor(batch_size, self.dim).normal_().requires_grad_().to(self.device)
        logp = -0.5 * x.pow(2).add(math.log(2 * math.pi* sigma**2)).sum(1) 
        x = x*sigma
        return self.integrate(x, logp, sign=1)

    def nll(self, x):
        '''
        integrate backwards, thus it returns logp(0) - logp(T)
        '''
        logp = torch.zeros(x.shape[0], device=x.device) 
        x, logp = self.integrate(x, logp, sign=-1)
        return logp + 0.5 * x.pow(2).add(math.log(2 * math.pi)).sum(1)

if __name__=='__main__':
    pass 
