'''
Quantum Measurement Classfiication Models
'''

import tensorflow as tf
from tensorflow.python.keras.engine import data_adapter
import numpy as np
from . import layers

class QMClassifier(tf.keras.Model):
    """
    A Quantum Measurement Classifier model.
    Arguments:
        fm_x: Quantum feature map layer for inputs
        fm_y: Quantum feature map layer for outputs
        dim_x: dimension of the input quantum feature map
        dim_y: dimension of the output representation
    """
    def __init__(self, fm_x, fm_y, dim_x, dim_y):
        super(QMClassifier, self).__init__()
        self.fm_x = fm_x
        self.fm_y = fm_y
        self.qm = layers.QMeasureClassif(dim_x=dim_x, dim_y=dim_y)
        self.dm2dist = layers.DensityMatrix2Dist()
        self.cp1 = layers.CrossProduct()
        self.cp2 = layers.CrossProduct()
        self.num_samples = tf.Variable(
            initial_value=0.,
            trainable=False     
            )

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        rho_y = self.qm(psi_x)
        probs = self.dm2dist(rho_y)
        return probs

    # @tf.function
    def call_train(self, x, y):
        if not self.qm.built:
            self.call(x)
        psi_x = self.fm_x(x)
        psi_y = self.fm_y(y)
        psi = self.cp1([psi_x, psi_y])
        rho = self.cp2([psi, tf.math.conj(psi)])
        num_samples = tf.cast(tf.shape(x)[0], rho.dtype)
        rho = tf.reduce_sum(rho, axis=0)
        self.num_samples.assign_add(num_samples)
        return rho

    def train_step(self, data):
        data =  data_adapter.expand_1d(data)
        x, y, sample_weight = data_adapter.unpack_x_y_sample_weight(data)
        if x.shape[1] is not None:
            rho = self.call_train(x, y)
            self.qm.weights[0].assign_add(rho)
        return {'loss': 0.0}

    def fit(self, *args, **kwargs):
        result = super(QMClassifier, self).fit(*args, **kwargs)
        self.qm.weights[0].assign(self.qm.weights[0] / self.num_samples)
        return result

    def get_rho(self):
        return self.qm.rho

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "dim_y": self.dim_y
        }
        base_config = super().get_config()
        return {**base_config, **config}


class QMClassifierSGD(tf.keras.Model):
    """
    A Quantum Measurement Classifier model trainable using
    gradient descent.

    Arguments:
        input_dim: dimension of the input
        dim_x: dimension of the input quantum feature map
        dim_y: dimension of the output representation
        num_eig: Number of eigenvectors used to represent the density matrix. 
                 a value of 0 or less implies num_eig = dim_x * dim_y
        gamma: float. Gamma parameter of the RBF kernel to be approximated.
        random_state: random number generator seed.
    """
    def __init__(self, input_dim, dim_x, dim_y, num_eig=0, gamma=1, random_state=None):
        super(QMClassifierSGD, self).__init__()
        self.fm_x = layers.QFeatureMapRFF(
            input_dim=input_dim,
            dim=dim_x, gamma=gamma, random_state=random_state)
        self.qm = layers.QMeasureClassifEig(dim_x=dim_x, dim_y=dim_y, num_eig=num_eig)
        self.dm2dist = layers.DensityMatrix2Dist()
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.gamma = gamma
        self.random_state = random_state

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        rho_y = self.qm(psi_x)
        probs = self.dm2dist(rho_y)
        return probs

    def set_rho(self, rho):
        return self.qm.set_rho(rho)

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "num_eig": self.num_eig,
            "gamma": self.gamma,
            "random_state": self.random_state
        }
        base_config = super().get_config()
        return {**base_config, **config}

class ComplexQMClassifierSGD(tf.keras.Model):
    """
    A Quantum Measurement Classifier model trainable using
    gradient descent with complex terms.

    Arguments:
        input_dim: dimension of the input
        dim_x: dimension of the input quantum feature map
        dim_y: dimension of the output representation
        num_eig: Number of eigenvectors used to represent the density matrix. 
                 a value of 0 or less implies num_eig = dim_x * dim_y
        gamma: float. Gamma parameter of the RBF kernel to be approximated.
        random_state: random number generator seed.
    """
    def __init__(self, input_dim, dim_x, dim_y, num_eig=0, gamma=1, random_state=None, train_ffs = True):
        super(ComplexQMClassifierSGD, self).__init__()
        self.fm_x = layers.QFeatureMapComplexRFF(
            input_dim=input_dim,
            dim=dim_x, gamma=gamma, random_state=random_state, train_ffs = train_ffs)
        self.qm = layers.ComplexQMeasureClassifEig(dim_x=dim_x, dim_y=dim_y, num_eig=num_eig)
        self.dm2dist = layers.ComplexDensityMatrix2Dist()
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.gamma = gamma
        self.random_state = random_state

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        rho_y = self.qm(psi_x)
        probs = self.dm2dist(rho_y)
        return probs

    def set_rho(self, rho):
        return self.qm.set_rho(rho)

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "num_eig": self.num_eig,
            "gamma": self.gamma,
            "random_state": self.random_state
        }
        base_config = super().get_config()
        return {**base_config, **config}

class QMDensity(tf.keras.Model):
    """
    A Quantum Measurement Density Estimation model.
    Arguments:
        fm_x: Quantum feature map layer for inputs
        dim_x: dimension of the input quantum feature map
    """
    def __init__(self, fm_x, dim_x):
        super(QMDensity, self).__init__()
        self.fm_x = fm_x
        self.dim_x = dim_x
        self.qmd = layers.QMeasureDensity(dim_x)
        self.cp = layers.CrossProduct()
        self.num_samples = tf.Variable(
            initial_value=0.,
            trainable=False     
            )

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs = self.qmd(psi_x)
        return probs

    @tf.function
    def call_train(self, x):
        if not self.qmd.built:
            self.call(x)
        psi = self.fm_x(x)
        rho = self.cp([psi, tf.math.conj(psi)])
        num_samples = tf.cast(tf.shape(x)[0], rho.dtype)
        rho = tf.reduce_sum(rho, axis=0)
        self.num_samples.assign_add(num_samples)
        return rho

    def train_step(self, data):
        data =  data_adapter.expand_1d(data)
        x, y, sample_weight = data_adapter.unpack_x_y_sample_weight(data)
        if x.shape[1] is not None:
            rho = self.call_train(x)
            self.qmd.weights[0].assign_add(rho)
        return {}

    def fit(self, *args, **kwargs):
        result = super(QMDensity, self).fit(*args, **kwargs)
        self.qmd.weights[0].assign(self.qmd.weights[0] / self.num_samples)
        return result

    def get_config(self):
        base_config = super().get_config()
        return {**base_config}
    
class ComplexQMDensity(tf.keras.Model):
    """
    A Quantum Measurement Density Estimation model.
    Arguments:
        fm_x: Quantum feature map layer for inputs
        dim_x: dimension of the input quantum feature map
    """
    def __init__(self, fm_x, dim_x):
        super(ComplexQMDensity, self).__init__()
        self.fm_x = fm_x
        self.dim_x = dim_x
        self.qmd = layers.ComplexQMeasureDensity(dim_x)
        self.cp = layers.CrossProduct()
        self.num_samples = tf.Variable(
            initial_value=0.,
            trainable=False     
            )

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs = self.qmd(psi_x)
        return probs

    @tf.function
    def call_train(self, x):
        if not self.qmd.built:
            self.call(x)
        psi = self.fm_x(x)
        rho = self.cp([psi, tf.math.conj(psi)])
        num_samples = tf.cast(tf.shape(x)[0], tf.float32)
        rho = tf.reduce_sum(rho, axis=0)
        self.num_samples.assign_add(num_samples)
        return rho

    def train_step(self, data):
        data =  data_adapter.expand_1d(data)
        x, y, sample_weight = data_adapter.unpack_x_y_sample_weight(data)
        if x.shape[1] is not None:
            rho = self.call_train(x)
            self.qmd.weights[0].assign_add(rho)
        return {}

    def fit(self, *args, **kwargs):
        result = super(ComplexQMDensity, self).fit(*args, **kwargs)
        self.num_samples = tf.cast(self.num_samples, tf.complex64)
        self.qmd.weights[0].assign(self.qmd.weights[0] / self.num_samples)
        return result

    def get_config(self):
        base_config = super().get_config()
        return {**base_config}

class QMDensitySGD(tf.keras.Model):
    """
    A Quantum Measurement Density Estimation modeltrainable using
    gradient descent.
    Arguments:
        input_dim: dimension of the input
        dim_x: dimension of the input quantum feature map
        num_eig: Number of eigenvectors used to represent the density matrix. 
                 a value of 0 or less implies num_eig = dim_x
        gamma: float. Gamma parameter of the RBF kernel to be approximated.
        random_state: random number generator seed.
    """
    def __init__(self, input_dim, dim_x, num_eig=0, gamma=1, random_state=None):
        super(QMDensitySGD, self).__init__()
        self.fm_x = layers.QFeatureMapRFF(
            input_dim=input_dim,
            dim=dim_x, gamma=gamma, random_state=random_state)
        self.qmd = layers.QMeasureDensityEig(dim_x=dim_x, num_eig=num_eig)
        self.num_eig = num_eig
        self.dim_x = dim_x
        self.gamma = gamma
        self.random_state = random_state

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs = self.qmd(psi_x)
        self.add_loss(-tf.reduce_sum(tf.math.log(probs)))
        return probs

    def set_rho(self, rho):
        return self.qmd.set_rho(rho)

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "gamma": self.gamma,
            "random_state": self.random_state
        }
        base_config = super().get_config()
        return {**base_config, **config}

class DMKDClassifier(tf.keras.Model):
    """
    A Quantum Measurement Kernel Density Classifier model.
    Arguments:
        fm_x: Quantum feature map layer for inputs
        dim_x: dimension of the input quantum feature map
        num_classes: int number of classes
    """
    def __init__(self, fm_x, dim_x, num_classes=2):
        super(DMKDClassifier, self).__init__()
        self.fm_x = fm_x
        self.dim_x = dim_x
        self.num_classes = num_classes
        self.qmd = []
        for _ in range(num_classes):
            self.qmd.append(layers.QMeasureDensity(dim_x))
        self.cp = layers.CrossProduct()
        self.num_samples = tf.Variable(
            initial_value=tf.zeros((num_classes,)),
            trainable=False
            )

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs = []
        for i in range(self.num_classes):
            probs.append(self.qmd[i](psi_x))
        posteriors = tf.stack(probs, axis=-1)
        posteriors = (posteriors / 
            tf.expand_dims(tf.reduce_sum(posteriors, axis=-1), axis=-1))
        return posteriors

    @tf.function
    def call_train(self, x, y):
        if not self.qmd[0].built:
            self.call(x)
        psi = self.fm_x(x) # shape (bs, dim_x)
        rho = self.cp([psi, tf.math.conj(psi)]) # shape (bs, dim_x, dim_x)
        ohy = tf.keras.backend.one_hot(y, self.num_classes)
        ohy = tf.reshape(ohy, (-1, self.num_classes))
        num_samples = tf.squeeze(tf.reduce_sum(ohy, axis=0))
        ohy = tf.expand_dims(ohy, axis=-1) 
        ohy = tf.expand_dims(ohy, axis=-1) # shape (bs, num_classes, 1, 1)
        rhos = ohy * tf.expand_dims(rho, axis=1) # shape (bs, num_classes, dim_x, dim_x)
        rhos = tf.reduce_sum(rhos, axis=0) # shape (num_classes, dim_x, dim_x)
        self.num_samples.assign_add(num_samples)
        return rhos

    def train_step(self, data):
        data =  data_adapter.expand_1d(data)
        x, y, sample_weight = data_adapter.unpack_x_y_sample_weight(data)
        if x.shape[1] is not None:
            rhos = self.call_train(x, y)
            for i in range(self.num_classes):
                self.qmd[i].weights[0].assign_add(rhos[i])
        return {}

    def fit(self, *args, **kwargs):
        result = super(DMKDClassifier, self).fit(*args, **kwargs)
        for i in range(self.num_classes):
            self.qmd[i].weights[0].assign(self.qmd[i].weights[0] /
                                          self.num_samples[i])
        return result

    def get_rhos(self):
        weights = [qmd.weights[0] for qmd in self.qmd]
        return weights

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "num_classes": self.num_classes
        }
        base_config = super().get_config()
        return {**base_config, **config}

class ComplexDMKDClassifier(tf.keras.Model):
    """
    A Quantum Measurement Kernel Density Classifier model with complex terms.
    Arguments:
        fm_x: Quantum feature map layer for inputs
        dim_x: dimension of the input quantum feature map
        num_classes: int number of classes
    """
    def __init__(self, fm_x, dim_x, num_classes=2):
        super(ComplexDMKDClassifier, self).__init__()
        self.fm_x = fm_x
        self.dim_x = dim_x
        self.num_classes = num_classes
        self.qmd = []
        for _ in range(num_classes):
            self.qmd.append(layers.ComplexQMeasureDensity(dim_x))
        self.cp = layers.CrossProduct()
        self.num_samples = tf.Variable(
            initial_value=tf.zeros((num_classes,)),
            trainable=False
            )

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs = []
        for i in range(self.num_classes):
            probs.append(self.qmd[i](psi_x))
        posteriors = tf.stack(probs, axis=-1)
        posteriors = posteriors / tf.expand_dims(tf.reduce_sum(posteriors, axis=-1), axis=-1)
        return posteriors

    @tf.function
    def call_train(self, x, y):
        if not self.qmd[0].built:
            self.call(x)
        psi = self.fm_x(x) # shape (bs, dim_x)
        rho = self.cp([psi, tf.math.conj(psi)]) # shape (bs, dim_x, dim_x)
        ohy = tf.keras.backend.one_hot(y, self.num_classes)
        ohy = tf.reshape(ohy, (-1, self.num_classes))
        num_samples = tf.squeeze(tf.reduce_sum(ohy, axis=0))
        ohy = tf.expand_dims(ohy, axis=-1) 
        ohy = tf.expand_dims(ohy, axis=-1) # shape (bs, num_classes, 1, 1)
        rhos = tf.cast(ohy, tf.complex64) * tf.expand_dims(rho, axis=1) # shape (bs, num_classes, dim_x, dim_x)
        rhos = tf.reduce_sum(rhos, axis=0) # shape (num_classes, dim_x, dim_x)
        self.num_samples.assign_add(num_samples)
        return rhos

    def train_step(self, data):
        data =  data_adapter.expand_1d(data)
        x, y, sample_weight = data_adapter.unpack_x_y_sample_weight(data)
        rhos = self.call_train(x, y)
        if x.shape[1] is not None:
            for i in range(self.num_classes):
                self.qmd[i].weights[0].assign_add(rhos[i])
        return {}

    def fit(self, *args, **kwargs):
        result = super(ComplexDMKDClassifier, self).fit(*args, **kwargs)
        for i in range(self.num_classes):
            self.qmd[i].weights[0].assign(self.qmd[i].weights[0] /
                                          tf.cast(self.num_samples[i], tf.complex64))
        return result

    def get_rhos(self):
        weights = [qmd.weights[0] for qmd in self.qmd]
        return weights

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "num_classes": self.num_classes
        }
        base_config = super().get_config()
        return {**base_config, **config}

class DMKDClassifierSGD(tf.keras.Model):
    """
    A Quantum Measurement Kernel Density Classifier model trainable using
    gradient descent.

    Arguments:
        input_dim: dimension of the input
        dim_x: dimension of the input quantum feature map
        num_classes: number of classes
        num_eig: Number of eigenvectors used to represent the density matrix. 
                 a value of 0 or less implies num_eig = dim_x 
        gamma: float. Gamma parameter of the RBF kernel to be approximated
        random_state: random number generator seed
    """
    def __init__(self, input_dim, dim_x, num_classes, num_eig=0, gamma=1, random_state=None):
        super(DMKDClassifierSGD, self).__init__()
        self.fm_x = layers.QFeatureMapRFF(
            input_dim=input_dim,
            dim=dim_x, gamma=gamma, random_state=random_state)
        self.dim_x = dim_x
        self.num_classes = num_classes
        self.qmd = []
        for _ in range(num_classes):
            self.qmd.append(layers.QMeasureDensityEig(dim_x, num_eig))
        self.gamma = gamma
        self.random_state = random_state

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs = []
        for i in range(self.num_classes):
            probs.append(self.qmd[i](psi_x))
        posteriors = tf.stack(probs, axis=-1)
        posteriors = (posteriors / 
                      tf.expand_dims(tf.reduce_sum(posteriors, axis=-1), axis=-1))
        return posteriors

    def set_rhos(self, rhos):
        for i in range(self.num_classes):
            self.qmd[i].set_rho(rhos[i])
        return

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "num_classes": self.num_classes,
            "num_eig": self.num_eig,
            "gamma": self.gamma,
            "random_state": self.random_state
        }
        base_config = super().get_config()
        return {**base_config, **config}

class ComplexDMKDClassifierSGD(tf.keras.Model):
    """
    A Quantum Measurement Kernel Density Classifier model trainable using
    gradient descent using complex random fourier features.

    Arguments:
        input_dim: dimension of the input
        dim_x: dimension of the input quantum feature map
        num_classes: number of classes
        num_eig: Number of eigenvectors used to represent the density matrix. 
                 a value of 0 or less implies num_eig = dim_x 
        gamma: float. Gamma parameter of the RBF kernel to be approximated
        random_state: random number generator seed
    """
    def __init__(self, input_dim, dim_x, num_classes, 
                 num_eig=0, gamma=1, random_state=None):
        super(ComplexDMKDClassifierSGD, self).__init__()
        self.fm_x = layers.QFeatureMapComplexRFF(
            input_dim=input_dim,
            dim=dim_x, gamma=gamma, random_state=random_state)
        self.dim_x = dim_x
        self.num_classes = num_classes
        self.qmd = []
        for _ in range(num_classes):
            self.qmd.append(layers.ComplexQMeasureDensityEig(dim_x, num_eig))
        self.gamma = gamma
        self.random_state = random_state

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs = []
        for i in range(self.num_classes):
            probs.append(self.qmd[i](psi_x))
        posteriors = tf.stack(probs, axis=-1)
        posteriors = (posteriors / 
                      tf.expand_dims(tf.reduce_sum(posteriors, axis=-1), axis=-1))
        return posteriors

    def set_rhos(self, rhos):
        for i in range(self.num_classes):
            self.qmd[i].set_rho(rhos[i])
        return

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "num_classes": self.num_classes,
            "num_eig": self.num_eig,
            "gamma": self.gamma,
            "random_state": self.random_state
        }
        base_config = super().get_config()
        return {**base_config, **config}

class ComplexDMKDRegressor(tf.keras.Model):
    """
    A Quantum Measurement Kernel Density Regressor model.
    Arguments:
        fm_x: Quantum feature map layer for inputs
        dim_x: dimension of the input quantum feature map
    """
    def __init__(self, fm_x, dim_x):
        super(ComplexDMKDRegressor, self).__init__()
        self.fm_x = fm_x
        self.dim_x = dim_x
        self.qmd = layers.ComplexQMeasureDensity(dim_x)
        self.qmr = layers.ComplexQMeasureDensity(dim_x)
        self.cpd = layers.CrossProduct()
        self.cpr = layers.CrossProduct()
        self.num_samples = tf.Variable(
            initial_value=0.,
            trainable=False
            )

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        probs_de = self.qmd(psi_x)
        probs_reg = self.qmr(psi_x)
        probs = probs_reg / probs_de
        probs = tf.cast(probs, tf.float32)
        return probs

    @tf.function
    def call_train_de(self, x):
        if not self.qmd.built:
            self.call(x)
        psi = self.fm_x(x)
        rho_de = self.cpd([psi, tf.math.conj(psi)])
        num_samples = tf.cast(tf.shape(x)[0], tf.float32)
        rho_de = tf.reduce_sum(rho_de, axis=0)
        self.num_samples.assign_add(num_samples)
        return rho_de

    @tf.function
    def call_train_reg(self, x, y):
        if not self.qmr.built:
            self.call(x)
        psi = self.fm_x(x)
        y = tf.cast(tf.expand_dims(y, axis=-1), tf.complex64)
        rho_reg = y*self.cpr([psi, tf.math.conj(psi)])
        num_samples = tf.cast(tf.shape(x)[0], tf.float32)
        rho_reg = tf.reduce_sum(rho_reg, axis=0)
        self.num_samples.assign_add(num_samples)
        return rho_reg

    def train_step(self, data):
        data =  data_adapter.expand_1d(data)
        x, y, sample_weight = data_adapter.unpack_x_y_sample_weight(data)
        if x.shape[1] is not None:
            rho_de = self.call_train_de(x)
            rho_reg = self.call_train_reg(x, y)
            self.qmd.weights[0].assign_add(rho_de)
            self.qmr.weights[0].assign_add(rho_reg)
        return {}

    def fit(self, *args, **kwargs):
        result = super(ComplexDMKDRegressor, self).fit(*args, **kwargs)
        self.num_samples = tf.cast(self.num_samples, tf.complex64)
        self.qmd.weights[0].assign(self.qmd.weights[0] / self.num_samples)
        self.qmr.weights[0].assign(self.qmr.weights[0] / self.num_samples)
        return result

    def get_config(self):
        base_config = super().get_config()
        return {**base_config}
    
class ComplexDMKDRegressorSGD:
    r"""
    Defines the ready-to-use Density matrix kernel density regression (DMKDR) model
     using the TensorFlow/Keras API. Any additional argument in the methods has to be Keras-compliant.

    Args:
        auto_compile: A boolean to autocompile the model using default settings. (Default True).

    Returns:
        An instantiated model ready to train with ad-hoc data.

    """
    def __init__(self, input_dim, num_ffs, y_min, y_max, num_eig=0, gamma=1, batch_size = 16, learning_rate = 0.0005, random_state=None, train_ffs = True, auto_compile=True):

        self.model = ComplexQMClassifierSGD(input_dim = input_dim, dim_x = num_ffs, dim_y = 2, num_eig=num_eig, gamma=gamma, random_state=random_state, train_ffs = train_ffs)
        self.num_ffs = num_ffs
        self.gamma = gamma
        self.y_min = y_min
        self.y_max = y_max
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.random_state = random_state

        if auto_compile:
            self.compile()

    def preprocess_outputs(
            self,
            y_train,
            **kwargs):
        r"""
        Method to preprocess the outputs y_train.

        Args:
            y_train:
            **kwargs: Any additional argument.

        Returns:
            new_outputs
        """

        y_normalized = (y_train - self.y_min)/(self.y_max - self.y_min)
        y_normalized_oh = np.zeros((y_normalized.shape[0], 2))
        y_normalized_oh[:, 0], y_normalized_oh[:, 1] = y_normalized.ravel(), (1 - y_normalized).ravel()

        return y_normalized_oh

    def compile(
            self,
            optimizer=tf.keras.optimizers.Adam,
            **kwargs):
        r"""
        Method to compile the model.

        Args:
            optimizer:
            **kwargs: Any additional argument.

        Returns:
            None.
        """
        self.model.compile(
            loss = "categorical_crossentropy",
            optimizer=optimizer(self.learning_rate),
            metrics=['mean_squared_error'],
            **kwargs
        )

    def fit(self, x_train, y_train, batch_size=16, epochs = 30, **kwargs):
        r"""
        Method to fit (train) the model using the ad-hoc dataset.

        Args:
            x_train:
            y_train:
            batch_size:
            epochs:
            **kwargs: Any additional argument.

        Returns:
            None.
        """
        y_preprocessed = self.preprocess_outputs(y_train)
        self.model.fit(x_train, y_preprocessed, batch_size = self.batch_size, epochs = epochs, **kwargs)

    def predict(self, x_test):
      r"""
      Method to make predictions with the trained model.

      Args:
          x_test:

      Returns:
          The predictions of the predicted regression of the input data.
      """
      return ((self.y_max - self.y_min)*self.model.predict(x_test) + self.y_min)[:, 0]

class QMRegressor(tf.keras.Model):
    """
    A Quantum Measurement Regression model.
    Arguments:
        fm_x: Quantum feature map layer for inputs
        fm_y: Quantum feature map layer for outputs
        dim_x: dimension of the input quantum feature map
        dim_y: dimension of the output quantum feature map
    """
    def __init__(self, fm_x, fm_y, dim_x, dim_y):
        super(QMRegressor, self).__init__()
        self.fm_x = fm_x
        self.fm_y = fm_y
        self.qm = layers.QMeasureClassif(dim_x=dim_x, dim_y=dim_y)
        self.dmregress = layers.DensityMatrixRegression()
        self.cp1 = layers.CrossProduct()
        self.cp2 = layers.CrossProduct()
        self.num_samples = tf.Variable(
            initial_value=0.,
            trainable=False     
            )

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        rho_y = self.qm(psi_x)
        mean_var = self.dmregress(rho_y)
        return mean_var

    @tf.function
    def call_train(self, x, y):
        if not self.qm.built:
            self.call(x)
        psi_x = self.fm_x(x)
        psi_y = self.fm_y(y)
        psi = self.cp1([psi_x, psi_y])
        rho = self.cp2([psi, tf.math.conj(psi)])
        num_samples = tf.cast(tf.shape(x)[0], rho.dtype)
        rho = tf.reduce_sum(rho, axis=0)
        self.num_samples.assign_add(num_samples)
        return rho

    def train_step(self, data):
        data =  data_adapter.expand_1d(data)
        x, y, sample_weight = data_adapter.unpack_x_y_sample_weight(data)
        if x.shape[1] is not None:
            rho = self.call_train(x, y)
            self.qm.weights[0].assign_add(rho)
        return {}

    def fit(self, *args, **kwargs):
        result = super(QMRegressor, self).fit(*args, **kwargs)
        self.qm.weights[0].assign(self.qm.weights[0] / self.num_samples)
        return result

    def get_rho(self):
        return self.weights[2]

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "dim_y": self.dim_y
        }
        base_config = super().get_config()
        return {**base_config, **config}

class QMRegressorSGD(tf.keras.Model):
    """
    A Quantum Measurement Regressor model trainable using
    gradient descent.

    Arguments:
        input_dim: dimension of the input
        dim_x: dimension of the input quantum feature map
        dim_y: dimension of the output quantum feature map
        num_eig: Number of eigenvectors used to represent the density matrix. 
                 a value of 0 or less implies num_eig = dim_x * dim_y
        gamma: float. Gamma parameter of the RBF kernel to be approximated.
        random_state: random number generator seed.
    """
    def __init__(self, input_dim, dim_x, dim_y, num_eig=0, gamma=1, random_state=None):
        super(QMRegressorSGD, self).__init__()
        self.fm_x = layers.QFeatureMapRFF(
            input_dim=input_dim,
            dim=dim_x, gamma=gamma, random_state=random_state)
        self.qm = layers.QMeasureClassifEig(dim_x=dim_x, dim_y=dim_y, num_eig=num_eig)
        self.dmregress = layers.DensityMatrixRegression()
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.gamma = gamma
        self.random_state = random_state

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        rho_y = self.qm(psi_x)
        mean_var = self.dmregress(rho_y)
        return mean_var

    def set_rho(self, rho):
        return self.qm.set_rho(rho)

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "num_eig": self.num_eig,
            "gamma": self.gamma,
            "random_state": self.random_state
        }
        base_config = super().get_config()
        return {**base_config, **config}

class ComplexQMRegressorSGD(tf.keras.Model):
    """
    A Quantum Measurement Regressor model trainable using
    gradient descent with complex terms.

    Arguments:
        input_dim: dimension of the input
        dim_x: dimension of the input quantum feature map
        dim_y: dimension of the output quantum feature map
        num_eig: Number of eigenvectors used to represent the density matrix. 
                 a value of 0 or less implies num_eig = dim_x
        gamma: float. Gamma parameter of the RBF kernel to be approximated.
        random_state: random number generator seed.
    """
    def __init__(self, input_dim, dim_x, dim_y, num_eig=0, gamma=1, random_state=None):
        super(ComplexQMRegressorSGD, self).__init__()
        self.fm_x = layers.QFeatureMapComplexRFF(
            input_dim=input_dim,
            dim=dim_x, gamma=gamma, random_state=random_state)
        self.qm = layers.ComplexQMeasureClassifEig(dim_x=dim_x, dim_y=dim_y, num_eig=num_eig)
        self.dmregress = layers.ComplexDensityMatrixRegression()
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.gamma = gamma
        self.random_state = random_state

    def call(self, inputs):
        psi_x = self.fm_x(inputs)
        rho_y = self.qm(psi_x)
        mean_var = self.dmregress(rho_y)
        return mean_var

    def set_rho(self, rho):
        return self.qm.set_rho(rho)

    def get_config(self):
        config = {
            "dim_x": self.dim_x,
            "dim_y": self.dim_y,
            "num_eig": self.num_eig,
            "gamma": self.gamma,
            "random_state": self.random_state
        }
        base_config = super().get_config()
        return {**base_config, **config}