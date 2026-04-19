
# 16-bit encryption for now
class key_manager:
    def __init__(self):
        self.p = 71
        self.q = 919
        self.n = self.p * self.q 
        self.phi = (self.p-1)*(self.q-1)
        self.nAsBytes = self.n.to_bytes(2, 'big')
        self.eAsBytes = b'\x01\x00\x01'        # 65537
        self.privateKey = None
        
    def generate_public_key(self):
        publicKey = self.nAsBytes + self.eAsBytes
        return publicKey
    
    def generate_private_key(self):
        d = pow(int.from_bytes(self.eAsBytes), -1, self.phi)
        return (d, self.n)

        
        
    