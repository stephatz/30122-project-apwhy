import pandas as pd

### To run, we have to instantiate the following global parameters###

# 1) thresholds represent pre-defined cutoffs obtained from our literature review
thresholds = {
'type I crime': 10,
'type II crime': 30,
'rental affordability': 0.3,
'house price affordability': 4,
'time to cbd': 30,
'distance to cbd': 5000}

# 2) specify fixed cutoff as specified in AF method. 
#    Criteria is to censor data for non-deprived neighborhoods
k = 2

# 3) path to clean data (currently synthetic as we are still merging our dataset)
cleaned_data = "../data_bases/raw_data/Synthetic Data.csv"

class MultiDimensionalDeprivation:
    def __init__(self, k, cleaned_data, thresholds):
        '''
        constructor
        '''
        self.k = k
        self.data = pd.read_csv(cleaned_data)
        self.thresholds = thresholds
        self.indicators = list(thresholds.keys())
        
    def deprivation_matrix(self):
        '''
        This function computes a matrix of deprivation scores for n zipcodes (rows)
        in d dimensions (columns)
        Inputs:
        cleaned_data    : takes in cleaned processed data
        k               : fixed cutoff in AF method
        
        Returns deprivation scores as a pandas dataframe
        '''
        #Generate binary matrix y
        mat_y = pd.DataFrame(index=self.data.index, columns=self.indicators)
        self.data['deprivation_share'] = 0
        for ind in self.indicators:
            mat_y[ind] = (self.data[ind] >= self.thresholds[ind]).astype(int)
            self.data['deprivation_share'] += mat_y[ind]

        # for all zipcodes that has less than k deprivations assign all elements to
        # be 0
        mat_y[self.data['deprivation_share'] <= self.k] = 0
        
        return mat_y

    def normalized_gap(self):
        '''
        Computes the normalized gap - Matrix g^1 in AF method
        Represents the extent of deprivation in distance relative to thresholds
        Some prefer this matrix as it satisfies monotonicity

        Input: Matrix Y from fn:deprivation_matrix()
        Returns: Matrix g^1(k) as a pandas dataframe
        '''
        mat_y = self.deprivation_matrix()
        
        # Compute the normalized gap
        mat_g1 = pd.DataFrame(index=self.data.index, columns=self.indicators)
        for ind in self.indicators:
            mat_g1[ind] = (self.data[ind] - self.thresholds[ind]) / self.thresholds[ind]
        
        # Replace null and negative values with 0 
        mat_g1 = mat_g1.fillna(0)
        mat_g1[mat_g1 < 0] = 0
        
        # Apply mat_y to g1
        for ind in self.indicators:
            mat_g1[ind] *= mat_y[ind]

        return mat_g1

    def power_gap(self, n):
        '''
        Computes power gap - Matrix g^alpha (n = alpha).
        This matrix is used by policymakers to target the most deprived 
        neighborhoods first

        Input: Matrix g^1(k) from fn: normalized_gap()
        Returns: Matrix g^alpha(k) as a pandas dataframe
        '''
        mat_g2 = self.normalized_gap() ** n
        return mat_g2

    def deprivation_share(self):
        '''
        Computes M0 (Called Adjusted Headcount ratio in the AF method)
        The ratio is a metrics of structural deprivation for those 
        included in cutoff k.

        Input: Matrix Y from fn:deprivation_matrix()
        Returns: A ratio. 
        '''
        mat_y = self.deprivation_matrix()
        non_zero_rows = mat_y.any(axis=1)
        num_non_zero_rows = non_zero_rows.sum()
        denominator = num_non_zero_rows * mat_y.shape[1]
        deprivation_share = mat_y.sum().sum() / denominator

        return deprivation_share

    def adj_deprivation_gap(self):
        '''
        Computes Matrix M1 (called Adjusted Poverty gap in AF method)
        This matrix encodes averages matrix g1 to obtain the average gap 
        (satisfies monotonicity)

        Input: Matrix g1 from fn:normalized_gap()
        Returns: A ratio.
        '''
        mat_g1 = self.normalized_gap()
        non_zero_rows = mat_g1.any(axis=1)
        num_non_zero_rows = non_zero_rows.sum()
        denominator = num_non_zero_rows * mat_g1.shape[1]
        deprivation_share = mat_g1.sum().sum() / denominator

        return deprivation_share


    def pca_weights(self, matrix, n_comp=6, rotate_fn='oblimin'):
        '''
        Performs PCA to express deprivation weights in terms of their 
        var-covar matrix

        Input: Any Matrix g0, g1, ..., gn (depending on objective of analysis)
        n_comp equivalent to num of dimensions (default=6, when index expands, 
        this parameter is set based on scree plot and factor loadings)
        rotate_fn - function for factor rotations (generally: oblimin or varimax)
        Returns: PCA or Factor weights
        '''

        #PCA
        pca = PCA()
        pca.fit(matrix)

        #Generate scree plot
        plt.plot(range(1, len(pca.explained_variance_)+1),
        pca.explained_variance_, 'ro-', linewidth=2)
        plt.title('Scree Plot')
        plt.xlabel('Principal Component')
        plt.ylabel('Eigenvalues')
        plt.show()

        # Factor analysis - Express factors as rotations
        fa = FactorAnalyzer(n_factors=n_comp, rotation= rotate_fn)
        fa.fit(matrix)
        print(pd.DataFrame(fa.get_communalities(),index=matrix.columns,columns=['Communalities']))

        # Express weights as factor loadings
        weights = fa.loadings_
        weights = pd.DataFrame(weights, columns=self.indicators)

        # normalize each row to sum to 1 
        # (For principal components, not needed for factor loadings)
        #### weights = weights.abs().div(weights.abs().sum(axis=1), axis=0)
        
        return weights

    def weighted_deprivation_inx(self, matrix, weights):
        '''
        Computes weighted deprivation index for each zipcode

        Inputs: 
            matrix  - g0, g1, ..., gn 
            weights - a dataframe containing vectors of weights for 
                      each dimension
        Returns: Weighted deprivation index score for each zipcode 
        '''
        # Aggregate weights
        weights = weights.sum(axis=0)

        wgt_dpt_idx = matrix.dot(weights)
        return wgt_dpt_idx