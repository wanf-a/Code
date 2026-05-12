from sqlalchemy import Column, Date, Integer, Float
from app.db.session import Base

class PricePrediction(Base):
    __tablename__ = "price_predictions"
    
    # 注意：数据库列名使用 day，不是 date
    day = Column('day', Date, primary_key=True, index=True)
    period = Column('period', Integer, primary_key=True, index=True)
    true_price = Column('true_price', Float)
    
    # 预测模型字段 - 使用数据库实际的列名（大写）
    Mamba_q0_5 = Column('Mamba_q0.5', Float)
    TCN_q0_5 = Column('TCN_q0.5', Float)
    Ensemble_q0_5 = Column('Ensemble_q0.5', Float)
    NLinear_q0_5 = Column('NLinear_q0.5', Float)
    
    # 其他分位数（如果需要）
    Ensemble_q0_05 = Column('Ensemble_q0.05', Float)
    Ensemble_q0_25 = Column('Ensemble_q0.25', Float)
    Ensemble_q0_75 = Column('Ensemble_q0.75', Float)
    Ensemble_q0_95 = Column('Ensemble_q0.95', Float)
    
    # 为了方便代码访问，提供小写的 property（可选）
    @property
    def mamba_q0_5(self):
        return self.Mamba_q0_5
    
    @property
    def tcn_q0_5(self):
        return self.TCN_q0_5
    
    @property
    def ensemble_q0_5(self):
        return self.Ensemble_q0_5
    
    @property
    def naive(self):
        return self.NLinear_q0_5
