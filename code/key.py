
# 16-bit encryption for now
class key_manager:
    def __init__(self):
        self.p = 71
        self.q = 919
        self.n = self.p * self.q 
        self.phi = (self.p-1)*(self.q-1)
        self.nAsBytes = self.n.to_bytes(2, 'big')
        self.e = b'\x01\x00\x01'        # 65537
        
    def generate_public_key(self):
        publicKey = self.nAsBytes + self.e
        return publicKey

        
        
    
publicKeyMsg = b'\x01\x05\xA2\x04'